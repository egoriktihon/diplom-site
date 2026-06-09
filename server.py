import hashlib
import base64
import binascii
import json
import os
import secrets
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / ".data"
DB_PATH = DATA_DIR / "clinic.db"
UPLOADS_DIR = BASE_DIR / "uploads" / "doctors"
SERVICE_UPLOADS_DIR = BASE_DIR / "uploads" / "services"
PORT = int(os.environ.get("PORT", "8000"))
HOST = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
PRIVATE_NAMES = {
    ".data",
    ".venv",
    ".vscode",
    "tools",
    "__pycache__",
    "server.py",
    "api.php",
    "config.php",
    "database.sql",
    "doctor_accounts.txt",
    "Procfile",
    "requirements.txt",
}


def utc_now():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def password_digest(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def normalize_phone(phone):
    digits = "".join(char for char in (phone or "") if char.isdigit())
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    return f"+{digits}" if digits else ""


def get_connection():
    DATA_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    SERVICE_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = MEMORY")
    connection.execute("PRAGMA synchronous = NORMAL")
    return connection


def seed_defaults(connection):
    specialties_count = connection.execute("SELECT COUNT(*) FROM specialties").fetchone()[0]
    if specialties_count == 0:
        specialties = [
            ("Терапевт", "therapist"),
            ("Кардиолог", "cardiologist"),
            ("Невролог", "neurologist"),
            ("Стоматолог", "dentist"),
            ("Другое", "other"),
        ]
        connection.executemany(
            "INSERT INTO specialties (name, specialty_key, created_at) VALUES (?, ?, ?)",
            [(*specialty, utc_now()) for specialty in specialties],
        )

    admin_exists = connection.execute("SELECT 1 FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    if not admin_exists:
        connection.execute(
            """
            INSERT INTO users (full_name, phone, email, password_hash, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "Администратор клиники",
                "+7 (999) 000-00-01",
                "admin@clinic.local",
                password_digest("admin12345"),
                "admin",
                utc_now(),
            ),
        )

    doctors_count = connection.execute("SELECT COUNT(*) FROM doctors").fetchone()[0]
    if doctors_count == 0:
        doctors = [
            ("Иванов Сергей", "Терапевт", "therapist", "Стаж 10 лет", "Опытный терапевт. Специализация: профилактика заболеваний внутренних органов и сопровождение пациентов после обследований.", "foto/doktora/dok1.jpg"),
            ("Петрова Анна", "Кардиолог", "cardiologist", "Стаж 12 лет", "Кардиолог с международным опытом. Специализация: диагностика и лечение сердечно-сосудистых заболеваний.", "foto/doktora/dok2.jpg"),
            ("Сидоров Алексей", "Невролог", "neurologist", "Стаж 9 лет", "Невролог с опытом работы в ведущих клиниках. Специализация: головные боли, нарушения сна и патологии нервной системы.", "foto/doktora/dok3.jpg"),
            ("Кузнецова Мария", "Стоматолог", "dentist", "Стаж 11 лет", "Стоматолог с большим опытом работы в эстетической стоматологии. Специализация: лечение и профилактика зубов.", "foto/doktora/dok4.jpg"),
        ]
        connection.executemany(
            """
            INSERT INTO doctors (full_name, specialty_name, specialty_key, experience_text, description, image_path, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(*doctor, utc_now()) for doctor in doctors],
        )

    doctor_columns = {row["name"] for row in connection.execute("PRAGMA table_info(doctors)").fetchall()}
    if "specialty_id" in doctor_columns:
        specialty_map = {
            row["specialty_key"]: row["id"]
            for row in connection.execute("SELECT id, specialty_key FROM specialties").fetchall()
        }
        for doctor in connection.execute("SELECT id, specialty_key FROM doctors WHERE specialty_id IS NULL").fetchall():
            specialty_id = specialty_map.get(doctor["specialty_key"])
            if specialty_id:
                connection.execute("UPDATE doctors SET specialty_id = ? WHERE id = ?", (specialty_id, doctor["id"]))

    services_count = connection.execute("SELECT COUNT(*) FROM services").fetchone()[0]
    if services_count == 0:
        services = [
            ("Консультация терапевта", "Первичный прием, сбор анамнеза и рекомендации по лечению.", "Первичный и повторный прием терапевта с подробным разбором симптомов, рекомендациями и маршрутом дальнейшего обследования.", 1500, "foto/prices/pri1.png", "consultation"),
            ("Консультация кардиолога", "Диагностика и рекомендации при заболеваниях сердца и сосудов.", "Консультация кардиолога с анализом состояния сердечно-сосудистой системы и подбором тактики лечения.", 1800, "foto/prices/pri1.png", "consultation"),
            ("Консультация невролога", "Прием при головной боли, нарушениях сна и заболеваниях нервной системы.", "Подробный неврологический осмотр и рекомендации по дальнейшей диагностике и терапии.", 1800, "foto/prices/pri1.png", "consultation"),
            ("УЗИ органов брюшной полости", "Современное обследование для точной и быстрой диагностики.", "УЗИ-диагностика органов брюшной полости на современном оборудовании.", 2000, "foto/prices/pri2.png", "diagnostics"),
            ("УЗИ сердца", "Исследование сердечно-сосудистой системы с подробным заключением.", "Диагностика состояния сердца и клапанного аппарата с развернутым протоколом.", 2500, "foto/prices/pri2.png", "diagnostics"),
            ("Общий анализ крови", "Базовое лабораторное исследование для оценки состояния организма.", "Оперативное лабораторное исследование с понятной расшифровкой основных показателей.", 500, "foto/prices/pri3.png", "analysis"),
            ("Биохимический анализ крови", "Расширенная лабораторная диагностика основных показателей здоровья.", "Лабораторная оценка обменных процессов и работы внутренних органов.", 1200, "foto/prices/pri3.png", "analysis"),
            ("ЭКГ", "Оценка работы сердца для профилактики и диагностики нарушений.", "Электрокардиография для раннего выявления нарушений ритма и других изменений.", 1200, "foto/prices/pri4.png", "cardio"),
            ("Профилактический check-up", "Комплексное обследование для контроля здоровья и ранней диагностики.", "Комплексная программа обследований для взрослых и детей с индивидуальным графиком.", 3500, "foto/advantages/adv1.png", "checkup"),
            ("Индивидуальный план лечения", "Персональная программа наблюдения и лечения по результатам приема.", "Подбор терапии с учетом состояния пациента, образа жизни и истории болезни.", 2500, "foto/advantages/adv4.png", "treatment"),
        ]
        connection.executemany(
            """
            INSERT INTO services (name, short_description, full_description, price, image_path, category_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [(*service, utc_now()) for service in services],
        )

    service_columns = {row["name"] for row in connection.execute("PRAGMA table_info(services)").fetchall()}
    if "specialty_id" in service_columns:
        specialty_map = {
            row["specialty_key"]: row["id"]
            for row in connection.execute("SELECT id, specialty_key FROM specialties").fetchall()
        }
        assignments = {
            "Консультация терапевта": "therapist",
            "Консультация кардиолога": "cardiologist",
            "Консультация невролога": "neurologist",
            "УЗИ сердца": "cardiologist",
            "ЭКГ": "cardiologist",
            "Профилактический check-up": "therapist",
            "Индивидуальный план лечения": "therapist",
        }
        for service in connection.execute("SELECT id, name FROM services WHERE specialty_id IS NULL").fetchall():
            specialty_key = assignments.get(service["name"])
            specialty_id = specialty_map.get(specialty_key) if specialty_key else None
            if specialty_id:
                connection.execute("UPDATE services SET specialty_id = ? WHERE id = ?", (specialty_id, service["id"]))

    links_count = connection.execute("SELECT COUNT(*) FROM doctor_services").fetchone()[0]
    if links_count == 0:
        doctor_map = {
            row["full_name"]: row["id"]
            for row in connection.execute("SELECT id, full_name FROM doctors").fetchall()
        }
        service_map = {
            row["name"]: row["id"]
            for row in connection.execute("SELECT id, name FROM services").fetchall()
        }
        links = [
            ("Иванов Сергей", "Консультация терапевта"),
            ("Иванов Сергей", "Профилактический check-up"),
            ("Иванов Сергей", "Индивидуальный план лечения"),
            ("Петрова Анна", "Консультация кардиолога"),
            ("Петрова Анна", "УЗИ сердца"),
            ("Петрова Анна", "ЭКГ"),
            ("Сидоров Алексей", "Консультация невролога"),
            ("Сидоров Алексей", "Индивидуальный план лечения"),
            ("Кузнецова Мария", "Профилактический check-up"),
        ]
        connection.executemany(
            "INSERT INTO doctor_services (doctor_id, service_id) VALUES (?, ?)",
            [(doctor_map[d], service_map[s]) for d, s in links if d in doctor_map and s in service_map],
        )

    ensure_existing_doctor_accounts(connection)


def ensure_existing_doctor_accounts(connection):
    connection.execute("DELETE FROM doctors WHERE full_name LIKE 'Test Doctor %'")

    account_templates = {
        ("Салюк Е.А.", "Гинеколог"): ("+7 (900) 100-10-14", "salyuk.ea@clinic.local", "SalyukEA2026!"),
        ("Салюк Л.С.", "Гинеколог"): ("+7 (900) 100-10-15", "salyuk.ls@clinic.local", "SalyukLS2026!"),
        ("Малышева Н.Ф.", "Дерматовенеролог"): ("+7 (900) 100-10-16", "malysheva.nf@clinic.local", "MalyshevaNF2026!"),
        ("Суханова Е.Г.", "Кардиолог"): ("+7 (900) 100-10-17", "sukhanova.eg@clinic.local", "SukhanovaEG2026!"),
        ("Невоструев А.В.", "Массажист"): ("+7 (900) 100-10-18", "nevostruev.av@clinic.local", "NevostruevAV2026!"),
        ("Горшков А.В.", "Невролог"): ("+7 (900) 100-10-19", "gorshkov.nevrolog@clinic.local", "GorshkovN2026!"),
        ("Смирнов С.В.", "Оториноларинголог"): ("+7 (900) 100-10-20", "smirnov.sv@clinic.local", "SmirnovSV2026!"),
        ("Долженко Г.С.", "Терапевт"): ("+7 (900) 100-10-21", "dolzhenko.gs@clinic.local", "DolzhenkoGS2026!"),
        ("Горшков А.В.", "Травматолог"): ("+7 (900) 100-10-22", "gorshkov.travma@clinic.local", "GorshkovT2026!"),
        ("Борцов М.Ю.", "УЗИ"): ("+7 (900) 100-10-23", "bortsov.uzi@clinic.local", "BortsovUZI2026!"),
        ("Башлачёв В.А.", "Уролог"): ("+7 (900) 100-10-24", "bashlachev.va@clinic.local", "BashlachevVA2026!"),
        ("Борцов М.Ю.", "Хирург"): ("+7 (900) 100-10-25", "bortsov.surgeon@clinic.local", "BortsovH2026!"),
        ("Ароян С.А.", "Эндокринолог"): ("+7 (900) 100-10-26", "aroyan.sa@clinic.local", "AroyanSA2026!"),
    }

    doctors = connection.execute(
        "SELECT id, full_name, specialty_name FROM doctors ORDER BY id ASC"
    ).fetchall()
    for doctor in doctors:
        account = account_templates.get((doctor["full_name"], doctor["specialty_name"]))
        if not account:
            continue
        exists = connection.execute(
            "SELECT 1 FROM users WHERE role = 'doctor' AND doctor_id = ? LIMIT 1",
            (doctor["id"],),
        ).fetchone()
        if exists:
            continue
        phone, email, password = account
        conflict = connection.execute(
            "SELECT 1 FROM users WHERE email = ? OR phone = ? LIMIT 1",
            (email, phone),
        ).fetchone()
        if conflict:
            continue
        connection.execute(
            """
            INSERT INTO users (full_name, phone, email, password_hash, role, doctor_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (doctor["full_name"], phone, email, password_digest(password), "doctor", doctor["id"], utc_now()),
        )


def init_db():
    with get_connection() as connection:
        users_info = connection.execute("PRAGMA table_info(users)").fetchall()
        if users_info:
            user_columns = {row["name"] for row in users_info}
            if "role" not in user_columns:
                connection.executescript(
                    """
                    DROP TABLE IF EXISTS doctor_services;
                    DROP TABLE IF EXISTS appointments;
                    DROP TABLE IF EXISTS services;
                    DROP TABLE IF EXISTS doctors;
                    DROP TABLE IF EXISTS sessions;
                    DROP TABLE IF EXISTS users;
                    """
                )

        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'patient',
                doctor_id INTEGER,
                created_at TEXT NOT NULL
                ,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS specialties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                specialty_key TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS doctors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                specialty_id INTEGER,
                full_name TEXT NOT NULL,
                specialty_name TEXT NOT NULL,
                specialty_key TEXT NOT NULL,
                experience_text TEXT NOT NULL,
                description TEXT NOT NULL,
                image_path TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (specialty_id) REFERENCES specialties(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                specialty_id INTEGER,
                name TEXT NOT NULL,
                short_description TEXT NOT NULL,
                full_description TEXT NOT NULL,
                price INTEGER NOT NULL DEFAULT 0,
                image_path TEXT NOT NULL,
                category_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (specialty_id) REFERENCES specialties(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS doctor_services (
                doctor_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                PRIMARY KEY (doctor_id, service_id),
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                doctor_id INTEGER,
                service_id INTEGER,
                title TEXT NOT NULL,
                subtitle TEXT NOT NULL,
                price TEXT DEFAULT '',
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'scheduled',
                notes TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE SET NULL,
                FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
            );
            """
        )
        appointment_columns = {row["name"] for row in connection.execute("PRAGMA table_info(appointments)").fetchall()}
        user_columns = {row["name"] for row in connection.execute("PRAGMA table_info(users)").fetchall()}
        if "doctor_id" not in user_columns:
            connection.execute("ALTER TABLE users ADD COLUMN doctor_id INTEGER")
        doctor_columns = {row["name"] for row in connection.execute("PRAGMA table_info(doctors)").fetchall()}
        if "specialty_id" not in doctor_columns:
            connection.execute("ALTER TABLE doctors ADD COLUMN specialty_id INTEGER")
        service_columns = {row["name"] for row in connection.execute("PRAGMA table_info(services)").fetchall()}
        if "specialty_id" not in service_columns:
            connection.execute("ALTER TABLE services ADD COLUMN specialty_id INTEGER")
        if "doctor_id" not in appointment_columns:
            connection.executescript(
                """
                ALTER TABLE appointments RENAME TO appointments_old;
                CREATE TABLE appointments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    doctor_id INTEGER,
                    service_id INTEGER,
                    title TEXT NOT NULL,
                    subtitle TEXT NOT NULL,
                    price TEXT DEFAULT '',
                    appointment_date TEXT NOT NULL,
                    appointment_time TEXT NOT NULL,
                    notes TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (doctor_id) REFERENCES doctors(id) ON DELETE SET NULL,
                    FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL
                );
                INSERT INTO appointments (id, user_id, title, subtitle, price, appointment_date, appointment_time, notes, created_at)
                SELECT id, user_id, title, subtitle, price, appointment_date, appointment_time, notes, created_at
                FROM appointments_old;
                DROP TABLE appointments_old;
                """
            )
            appointment_columns = {row["name"] for row in connection.execute("PRAGMA table_info(appointments)").fetchall()}
        if "status" not in appointment_columns:
            connection.execute("ALTER TABLE appointments ADD COLUMN status TEXT NOT NULL DEFAULT 'scheduled'")
        seed_defaults(connection)
        connection.commit()


def file_extension_from_name(name):
    suffix = Path(name or "").suffix.lower()
    return suffix if suffix in {".png", ".jpg", ".jpeg", ".webp"} else ".png"


def save_doctor_image(image_data, image_name):
    if not image_data:
        return "foto/doktora/dok1.jpg"

    payload = image_data
    if "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        binary = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Не удалось обработать изображение врача.")

    extension = file_extension_from_name(image_name)
    filename = f"doctor-{int(datetime.utcnow().timestamp() * 1000)}{extension}"
    filepath = UPLOADS_DIR / filename
    filepath.write_bytes(binary)
    return f"uploads/doctors/{filename}"


def save_service_image(image_data, image_name):
    if not image_data:
        return "foto/prices/pri1.png"

    payload = image_data
    if "," in payload:
        payload = payload.split(",", 1)[1]

    try:
        binary = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError):
        raise ValueError("Не удалось обработать изображение услуги.")

    extension = file_extension_from_name(image_name)
    filename = f"service-{int(datetime.utcnow().timestamp() * 1000)}{extension}"
    filepath = SERVICE_UPLOADS_DIR / filename
    filepath.write_bytes(binary)
    return f"uploads/services/{filename}"


def user_payload(connection, user_id):
    user = connection.execute(
        "SELECT id, full_name, phone, email, role, doctor_id, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not user:
        return None

    appointments = connection.execute(
        """
        SELECT id, title, subtitle, price, appointment_date, appointment_time, status, notes, created_at
        FROM appointments
        WHERE user_id = ?
        ORDER BY appointment_date ASC, appointment_time ASC, id DESC
        """,
        (user_id,),
    ).fetchall()

    return {
        "id": user["id"],
        "full_name": user["full_name"],
        "phone": user["phone"],
        "email": user["email"],
        "role": user["role"],
        "doctor_id": user["doctor_id"],
        "created_at": user["created_at"],
        "appointments": [dict(row) for row in appointments],
    }


class ClinicHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def log_message(self, format, *args):
        return

    def guess_type(self, path):
        content_type = super().guess_type(path)
        if content_type in {"text/html", "text/css", "application/javascript", "text/javascript"}:
            return f"{content_type}; charset=utf-8"
        return content_type

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_json(self, payload, status=HTTPStatus.OK):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def is_private_path(self, path):
        parts = [part for part in Path(unquote(path)).parts if part not in {"/", "\\"}]
        return any(part in PRIVATE_NAMES or part.startswith(".") for part in parts)

    def parse_json_body(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(content_length) if content_length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self.send_json({"error": "Некорректный JSON."}, HTTPStatus.BAD_REQUEST)
            return None

    def get_token(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            return auth.split(" ", 1)[1].strip()
        return None

    def require_auth(self, connection):
        token = self.get_token()
        if not token:
            self.send_json({"error": "Требуется авторизация."}, HTTPStatus.UNAUTHORIZED)
            return None

        row = connection.execute("SELECT user_id FROM sessions WHERE token = ?", (token,)).fetchone()
        if not row:
            self.send_json({"error": "Сессия не найдена."}, HTTPStatus.UNAUTHORIZED)
            return None
        return row["user_id"]

    def require_admin(self, connection):
        user_id = self.require_auth(connection)
        if not user_id:
            return None
        role = connection.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
        if not role or role["role"] != "admin":
            self.send_json({"error": "Доступ только для администратора."}, HTTPStatus.FORBIDDEN)
            return None
        return user_id

    def require_doctor(self, connection):
        user_id = self.require_auth(connection)
        if not user_id:
            return None
        user = connection.execute("SELECT role, doctor_id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user or user["role"] != "doctor" or not user["doctor_id"]:
            self.send_json({"error": "Доступ только для врача."}, HTTPStatus.FORBIDDEN)
            return None
        return user

    def api_list_doctors(self, connection):
        rows = connection.execute(
            """
            SELECT d.id, d.specialty_id, d.full_name, d.specialty_name, d.specialty_key, d.experience_text, d.description, d.image_path, d.created_at,
                   u.email AS account_email,
                   GROUP_CONCAT(ds.service_id) AS service_ids
            FROM doctors d
            LEFT JOIN users u ON u.doctor_id = d.id AND u.role = 'doctor'
            LEFT JOIN doctor_services ds ON ds.doctor_id = d.id
            GROUP BY d.id
            ORDER BY d.id ASC
            """
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["service_ids"] = [int(value) for value in (item["service_ids"] or "").split(",") if value]
            items.append(item)
        return items

    def api_list_services(self, connection):
        rows = connection.execute(
            """
            SELECT s.id, s.specialty_id, s.name, s.short_description, s.full_description, s.price, s.image_path, s.category_key, s.created_at,
                   sp.name AS specialty_name, sp.specialty_key,
                   GROUP_CONCAT(ds.doctor_id) AS doctor_ids
            FROM services s
            LEFT JOIN specialties sp ON sp.id = s.specialty_id
            LEFT JOIN doctor_services ds ON ds.service_id = s.id
            GROUP BY s.id
            ORDER BY s.id ASC
            """
        ).fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["doctor_ids"] = [int(value) for value in (item["doctor_ids"] or "").split(",") if value]
            items.append(item)
        return items

    def api_list_specialties(self, connection):
        rows = connection.execute(
            "SELECT id, name, specialty_key, created_at FROM specialties ORDER BY name ASC"
        ).fetchall()
        return [dict(row) for row in rows]

    def api_list_doctor_appointments(self, connection, doctor_id):
        rows = connection.execute(
            """
            SELECT a.id, a.title, a.subtitle, a.price, a.appointment_date, a.appointment_time,
                   a.status, a.notes, a.created_at,
                   u.full_name AS patient_name, u.phone AS patient_phone, u.email AS patient_email
            FROM appointments a
            INNER JOIN users u ON u.id = a.user_id
            WHERE a.doctor_id = ?
            ORDER BY a.appointment_date ASC, a.appointment_time ASC, a.id DESC
            """,
            (doctor_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def handle_api(self):
        parsed = urlparse(self.path)
        action = parse_qs(parsed.query).get("action", [""])[0]
        method = self.command

        try:
            with get_connection() as connection:
                if action == "health" and method == "GET":
                    self.send_json({
                        "ok": True,
                        "database": str(DB_PATH),
                        "users_count": connection.execute("SELECT COUNT(*) FROM users").fetchone()[0],
                    })
                    return

                if action == "register" and method == "POST":
                    data = self.parse_json_body()
                    if data is None:
                        return
                    full_name = (data.get("full_name") or "").strip()
                    phone = normalize_phone(data.get("phone"))
                    email = (data.get("email") or "").strip().lower()
                    password = (data.get("password") or "").strip()
                    if not all([full_name, phone, email, password]):
                        self.send_json({"error": "Заполните все поля."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    exists = connection.execute("SELECT 1 FROM users WHERE email = ? OR phone = ? LIMIT 1", (email, phone)).fetchone()
                    if not exists:
                        exists = next(
                            (
                                row
                                for row in connection.execute("SELECT phone FROM users").fetchall()
                                if normalize_phone(row["phone"]) == phone
                            ),
                            None,
                        )
                    if exists:
                        self.send_json({"error": "Пользователь с таким email или телефоном уже существует."}, HTTPStatus.CONFLICT)
                        return
                    cursor = connection.execute(
                        "INSERT INTO users (full_name, phone, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                        (full_name, phone, email, password_digest(password), "patient", utc_now()),
                    )
                    token = secrets.token_urlsafe(32)
                    connection.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, cursor.lastrowid, utc_now()))
                    connection.commit()
                    self.send_json({"token": token, "user": user_payload(connection, cursor.lastrowid)}, HTTPStatus.CREATED)
                    return

                if action == "login" and method == "POST":
                    data = self.parse_json_body()
                    if data is None:
                        return
                    login = (data.get("login") or "").strip().lower()
                    login_phone = normalize_phone(login)
                    password = (data.get("password") or "").strip()
                    if not login or not password:
                        self.send_json({"error": "Введите логин и пароль."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    user = connection.execute(
                        "SELECT id, password_hash FROM users WHERE email = ? OR phone = ? OR phone = ? LIMIT 1",
                        (login, login, login_phone),
                    ).fetchone()
                    if not user and login_phone:
                        user = next(
                            (
                                row
                                for row in connection.execute("SELECT id, phone, password_hash FROM users").fetchall()
                                if normalize_phone(row["phone"]) == login_phone
                            ),
                            None,
                        )
                    if not user or user["password_hash"] != password_digest(password):
                        self.send_json({"error": "Неверный email, телефон или пароль."}, HTTPStatus.UNAUTHORIZED)
                        return
                    token = secrets.token_urlsafe(32)
                    connection.execute("INSERT INTO sessions (token, user_id, created_at) VALUES (?, ?, ?)", (token, user["id"], utc_now()))
                    connection.commit()
                    self.send_json({"token": token, "user": user_payload(connection, user["id"])})
                    return

                if action == "logout" and method == "POST":
                    token = self.get_token()
                    if token:
                        connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
                        connection.commit()
                    self.send_json({"ok": True})
                    return

                if action == "me" and method == "GET":
                    user_id = self.require_auth(connection)
                    if not user_id:
                        return
                    self.send_json({"user": user_payload(connection, user_id)})
                    return

                if action == "doctors" and method == "GET":
                    self.send_json({"doctors": self.api_list_doctors(connection)})
                    return

                if action == "services" and method == "GET":
                    self.send_json({"services": self.api_list_services(connection)})
                    return

                if action == "specialties" and method == "GET":
                    self.send_json({"specialties": self.api_list_specialties(connection)})
                    return

                if action == "appointments.busy" and method == "POST":
                    data = self.parse_json_body()
                    if data is None:
                        return
                    doctor_id = int(data.get("doctor_id") or 0)
                    appointment_date = (data.get("appointment_date") or "").strip()
                    if not doctor_id or not appointment_date:
                        self.send_json({"busy_times": []})
                        return
                    rows = connection.execute(
                        """
                        SELECT appointment_time
                        FROM appointments
                        WHERE doctor_id = ? AND appointment_date = ?
                          AND status IN ('scheduled', 'completed')
                        ORDER BY appointment_time ASC
                        """,
                        (doctor_id, appointment_date),
                    ).fetchall()
                    self.send_json({"busy_times": [str(row["appointment_time"])[:5] for row in rows]})
                    return

                if action == "appointments.create" and method == "POST":
                    user_id = self.require_auth(connection)
                    if not user_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    title = (data.get("title") or "").strip()
                    subtitle = (data.get("subtitle") or "").strip()
                    price = (data.get("price") or "").strip()
                    doctor_id = int(data.get("doctor_id") or 0)
                    service_id = int(data.get("service_id") or 0)
                    appointment_date = (data.get("appointment_date") or "").strip()
                    appointment_time = (data.get("appointment_time") or "").strip()
                    notes = (data.get("notes") or "").strip()
                    if not all([title, subtitle, appointment_date, appointment_time]):
                        self.send_json({"error": "Укажите дату, время и тип записи."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    if service_id:
                        service_exists = connection.execute("SELECT id, name FROM services WHERE id = ?", (service_id,)).fetchone()
                        if not service_exists:
                            self.send_json({"error": "Услуга не найдена."}, HTTPStatus.NOT_FOUND)
                            return
                    if doctor_id:
                        doctor_exists = connection.execute("SELECT id, full_name FROM doctors WHERE id = ?", (doctor_id,)).fetchone()
                        if not doctor_exists:
                            self.send_json({"error": "Врач не найден."}, HTTPStatus.NOT_FOUND)
                            return
                    if doctor_id and service_id:
                        relation = connection.execute(
                            "SELECT 1 FROM doctor_services WHERE doctor_id = ? AND service_id = ? LIMIT 1",
                            (doctor_id, service_id),
                        ).fetchone()
                        if not relation:
                            self.send_json({"error": "Этот врач не оказывает выбранную услугу."}, HTTPStatus.CONFLICT)
                            return
                    conflict = connection.execute(
                        """
                        SELECT 1
                        FROM appointments
                        WHERE doctor_id = ? AND appointment_date = ? AND appointment_time = ?
                          AND status IN ('scheduled', 'completed')
                        LIMIT 1
                        """,
                        (doctor_id if doctor_id else None, appointment_date, appointment_time),
                    ).fetchone()
                    if doctor_id and conflict:
                        self.send_json({"code": "appointment_time_busy", "error": "\u041d\u0435\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e \u0437\u0430\u043f\u0438\u0441\u0430\u0442\u044c\u0441\u044f \u043d\u0430 \u044d\u0442\u043e \u0432\u0440\u0435\u043c\u044f, \u043f\u043e\u0442\u043e\u043c\u0443 \u0447\u0442\u043e \u043e\u043d\u043e \u0443\u0436\u0435 \u0437\u0430\u043d\u044f\u0442\u043e."}, HTTPStatus.CONFLICT)
                        return
                    connection.execute(
                        """
                        INSERT INTO appointments (user_id, doctor_id, service_id, title, subtitle, price, appointment_date, appointment_time, notes, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (user_id, doctor_id or None, service_id or None, title, subtitle, price, appointment_date, appointment_time, notes, utc_now()),
                    )
                    connection.commit()
                    self.send_json({"ok": True}, HTTPStatus.CREATED)
                    return

                if action == "appointments.cancel" and method == "POST":
                    user_id = self.require_auth(connection)
                    if not user_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    appointment_id = int(data.get("id") or 0)
                    result = connection.execute("DELETE FROM appointments WHERE id = ? AND user_id = ?", (appointment_id, user_id))
                    connection.commit()
                    if result.rowcount == 0:
                        self.send_json({"error": "Запись не найдена."}, HTTPStatus.NOT_FOUND)
                        return
                    self.send_json({"ok": True})
                    return

                if action == "doctor.dashboard" and method == "GET":
                    doctor = self.require_doctor(connection)
                    if not doctor:
                        return
                    appointments = self.api_list_doctor_appointments(connection, doctor["doctor_id"])
                    self.send_json({"appointments": appointments})
                    return

                if action == "doctor.appointments.status" and method == "POST":
                    doctor = self.require_doctor(connection)
                    if not doctor:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    appointment_id = int(data.get("id") or 0)
                    status = (data.get("status") or "").strip()
                    allowed_statuses = {"completed", "no_show", "failed"}
                    if status not in allowed_statuses:
                        self.send_json({"error": "Некорректный статус записи."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    result = connection.execute(
                        "UPDATE appointments SET status = ? WHERE id = ? AND doctor_id = ?",
                        (status, appointment_id, doctor["doctor_id"]),
                    )
                    connection.commit()
                    if result.rowcount == 0:
                        self.send_json({"error": "Запись не найдена."}, HTTPStatus.NOT_FOUND)
                        return
                    self.send_json({"ok": True})
                    return

                if action == "admin.dashboard" and method == "GET":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    counts = {
                        "users": connection.execute("SELECT COUNT(*) FROM users WHERE role = 'patient'").fetchone()[0],
                        "doctor_accounts": connection.execute("SELECT COUNT(*) FROM users WHERE role = 'doctor'").fetchone()[0],
                        "doctors": connection.execute("SELECT COUNT(*) FROM doctors").fetchone()[0],
                        "specialties": connection.execute("SELECT COUNT(*) FROM specialties").fetchone()[0],
                        "services": connection.execute("SELECT COUNT(*) FROM services").fetchone()[0],
                        "appointments": connection.execute("SELECT COUNT(*) FROM appointments").fetchone()[0],
                    }
                    appointments = connection.execute(
                        """
                        SELECT a.id, a.title, a.subtitle, a.price, a.appointment_date, a.appointment_time, a.status, a.notes,
                               u.full_name AS patient_name, u.phone AS patient_phone, u.email AS patient_email,
                               d.full_name AS doctor_name
                        FROM appointments a
                        INNER JOIN users u ON u.id = a.user_id
                        LEFT JOIN doctors d ON d.id = a.doctor_id
                        ORDER BY a.appointment_date ASC, a.appointment_time ASC, a.id DESC
                        """
                    ).fetchall()
                    self.send_json({
                        "counts": counts,
                        "specialties": self.api_list_specialties(connection),
                        "doctors": self.api_list_doctors(connection),
                        "services": self.api_list_services(connection),
                        "appointments": [dict(row) for row in appointments],
                    })
                    return

                if action == "admin.doctors.create" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    specialty_id = int(data.get("specialty_id") or 0)
                    full_name = (data.get("full_name") or "").strip()
                    specialty_name = (data.get("specialty_name") or "").strip()
                    specialty_key = (data.get("specialty_key") or "other").strip()
                    experience_text = (data.get("experience_text") or "").strip()
                    description = (data.get("description") or "").strip()
                    account_login = (data.get("account_login") or "").strip().lower()
                    account_phone = normalize_phone(data.get("account_phone"))
                    account_password = (data.get("account_password") or "").strip()
                    image_path = save_doctor_image(data.get("image_data") or "", data.get("image_name") or "")
                    service_ids = data.get("service_ids") or []
                    if not all([full_name, specialty_name, experience_text, description, account_login, account_phone, account_password]):
                        self.send_json({"error": "Заполните все поля врача."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    exists = connection.execute(
                        "SELECT 1 FROM users WHERE email = ? OR phone = ? LIMIT 1",
                        (account_login, account_phone),
                    ).fetchone()
                    if exists:
                        self.send_json({"error": "Пользователь с таким логином или телефоном уже существует."}, HTTPStatus.CONFLICT)
                        return
                    cursor = connection.execute(
                        """
                        INSERT INTO doctors (specialty_id, full_name, specialty_name, specialty_key, experience_text, description, image_path, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (specialty_id or None, full_name, specialty_name, specialty_key, experience_text, description, image_path, utc_now()),
                    )
                    doctor_id = cursor.lastrowid
                    clean_service_ids = [int(value) for value in service_ids if str(value).isdigit()]
                    if clean_service_ids:
                        connection.executemany(
                            "INSERT INTO doctor_services (doctor_id, service_id) VALUES (?, ?)",
                            [(doctor_id, service_id) for service_id in clean_service_ids],
                        )
                    connection.execute(
                        """
                        INSERT INTO users (full_name, phone, email, password_hash, role, doctor_id, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (full_name, account_phone, account_login, password_digest(account_password), "doctor", doctor_id, utc_now()),
                    )
                    connection.commit()
                    self.send_json({"ok": True}, HTTPStatus.CREATED)
                    return

                if action == "admin.specialties.create" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    name = (data.get("name") or "").strip()
                    specialty_key = (data.get("specialty_key") or "").strip()
                    if not name or not specialty_key:
                        self.send_json({"error": "Введите название и ключ специальности."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    exists = connection.execute(
                        "SELECT 1 FROM specialties WHERE name = ? OR specialty_key = ? LIMIT 1",
                        (name, specialty_key),
                    ).fetchone()
                    if exists:
                        self.send_json({"error": "Такая специальность уже существует."}, HTTPStatus.CONFLICT)
                        return
                    connection.execute(
                        "INSERT INTO specialties (name, specialty_key, created_at) VALUES (?, ?, ?)",
                        (name, specialty_key, utc_now()),
                    )
                    connection.commit()
                    self.send_json({"ok": True}, HTTPStatus.CREATED)
                    return

                if action == "admin.services.create" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    specialty_id = int(data.get("specialty_id") or 0)
                    name = (data.get("name") or "").strip()
                    short_description = (data.get("short_description") or "").strip()
                    full_description = (data.get("full_description") or "").strip()
                    raw_price = str(data.get("price") or "").strip().replace(" ", "").replace(",", ".")
                    try:
                        price = int(float(raw_price))
                    except (ValueError, TypeError):
                        price = 0
                    image_path = save_service_image(data.get("image_data") or "", data.get("image_name") or "")
                    category_key = (data.get("category_key") or "general").strip()
                    if not name or price <= 0:
                        self.send_json({"error": "Укажите название услуги и цену больше нуля."}, HTTPStatus.UNPROCESSABLE_ENTITY)
                        return
                    connection.execute(
                        """
                        INSERT INTO services (specialty_id, name, short_description, full_description, price, image_path, category_key, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (specialty_id or None, name, short_description, full_description, price, image_path, category_key, utc_now()),
                    )
                    connection.commit()
                    self.send_json({"ok": True}, HTTPStatus.CREATED)
                    return

                if action == "admin.doctors.delete" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    doctor_id = int(data.get("id") or 0)
                    connection.execute("DELETE FROM users WHERE role = 'doctor' AND doctor_id = ?", (doctor_id,))
                    connection.execute("DELETE FROM doctors WHERE id = ?", (doctor_id,))
                    connection.commit()
                    self.send_json({"ok": True})
                    return

                if action == "admin.services.delete" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    connection.execute("DELETE FROM services WHERE id = ?", (int(data.get("id") or 0),))
                    connection.commit()
                    self.send_json({"ok": True})
                    return

                if action == "admin.specialties.delete" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    connection.execute("DELETE FROM specialties WHERE id = ?", (int(data.get("id") or 0),))
                    connection.commit()
                    self.send_json({"ok": True})
                    return

                if action == "admin.appointments.delete" and method == "POST":
                    admin_id = self.require_admin(connection)
                    if not admin_id:
                        return
                    data = self.parse_json_body()
                    if data is None:
                        return
                    result = connection.execute("DELETE FROM appointments WHERE id = ?", (int(data.get("id") or 0),))
                    connection.commit()
                    if result.rowcount == 0:
                        self.send_json({"error": "Запись не найдена."}, HTTPStatus.NOT_FOUND)
                        return
                    self.send_json({"ok": True})
                    return

                self.send_json({"error": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)
        except Exception as error:
            self.send_json({"error": f"Ошибка сервера: {error}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.path = "/index.html"
            return super().do_GET()
        if parsed.path == "/api":
            return self.handle_api()
        if self.is_private_path(parsed.path):
            self.send_json({"error": "Файл недоступен."}, HTTPStatus.NOT_FOUND)
            return
        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api":
            return self.handle_api()
        self.send_json({"error": "Маршрут не найден."}, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ClinicHandler)
    print(f"Server running at http://{HOST}:{PORT}")
    server.serve_forever()
