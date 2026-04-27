"""
timetable_db.py — SQLite interface for timetable problems.

Days and slots are fixed in the language (DAYS enum, MAX_SLOTS constant)
and are not stored here.

Schema
------
  problems(name TEXT PK)
  classes(problem TEXT, name TEXT, size INTEGER)
  subjects(problem TEXT, name TEXT)
  teachers(problem TEXT, name TEXT)
  rooms(problem TEXT, name TEXT, capacity INTEGER, room_type TEXT)
  requirements(problem TEXT, class TEXT, subject TEXT, periods INTEGER)
  can_teach(problem TEXT, teacher TEXT, subject TEXT)
  subject_room_type(problem TEXT, subject TEXT, room_type TEXT)
  teacher_unavailability(problem TEXT, teacher TEXT, day TEXT, slot INTEGER)
  soft_constraints(problem TEXT PK, max_consecutive_same_subj INT, max_teacher_periods_day INT)

Usage
-----
  from timetable_db import DB
  db = DB()                        # opens /tmp/timetable.db, seeds DEFAULT
  data = db.load("DEFAULT")        # returns problem dict
  db.save("MySchool", data)        # upsert
  db.delete("MySchool")
  names = db.list()
"""

import sqlite3

DB_PATH = "/tmp/timetable.db"

DEFAULT_NAME = "DEFAULT"

DEFAULT_DATA = {
    "classes": [
        {"name": "Year7A",  "size": 30},
        {"name": "Year7B",  "size": 28},
        {"name": "Year8A",  "size": 30},
        {"name": "Year8B",  "size": 27},
        {"name": "Year9A",  "size": 29},
        {"name": "Year9B",  "size": 26},
    ],
    "subjects": ["Math", "English", "Science", "History", "Geography", "French", "PE", "Art"],
    "teachers": [
        "Adams", "Brown", "Clarke", "Davies", "Evans",
        "Foster", "Green", "Harris", "Ito", "Jones",
    ],
    "rooms": [
        {"name": "R01",   "capacity": 32, "room_type": "standard"},
        {"name": "R02",   "capacity": 32, "room_type": "standard"},
        {"name": "R03",   "capacity": 32, "room_type": "standard"},
        {"name": "R04",   "capacity": 32, "room_type": "standard"},
        {"name": "Lab1",  "capacity": 30, "room_type": "lab"},
        {"name": "Lab2",  "capacity": 30, "room_type": "lab"},
        {"name": "Gym",   "capacity": 60, "room_type": "gym"},
        {"name": "ArtRm", "capacity": 32, "room_type": "art"},
    ],
    "requirements": {
        "Year7A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year7B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year8A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year8B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year9A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year9B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
    },
    # Each subject shared by 2+ teachers so no one exceeds 4 periods/day.
    # Math(24/wk): Adams+Clarke -> ~12 each = 2.4/day
    # English(24/wk): Brown+Evans+Jones -> ~8 each = 1.6/day
    # Science(18/wk): Davies+Green -> ~9 each = 1.8/day
    "can_teach": {
        "Adams":  ["Math"],
        "Brown":  ["English", "History"],
        "Clarke": ["Math", "French"],
        "Davies": ["Science", "Geography"],
        "Evans":  ["English", "Art"],
        "Foster": ["History", "Geography"],
        "Green":  ["Science"],
        "Harris": ["PE"],
        "Ito":    ["French", "Art"],
        "Jones":  ["English", "PE"],
    },
    # Hard constraint: subject requires a specific room type.
    # Omit a subject to allow any room.
    "subject_room_type": {
        "Science": "lab",
        "PE":      "gym",
        "Art":     "art",
    },
    # Hard constraint: blocked (teacher, day, slot) triples.
    "teacher_unavailability": [],
    # Hard constraints (enforced during search — no valid solution violates these).
    "hard_constraints": {
        "max_consecutive_same_subj": 2,   # max run of same subject in a row for a class
        "max_teacher_periods_day":   4,   # max periods a teacher teaches per day
    },
    # Soft constraints — scored after solving; lower is better.
    "soft_constraints": {
        "weight_class_holes":          1,   # free periods between lessons in a class day
        "weight_avoid_first_slot":     2,   # lessons scheduled in slot 1
        "weight_avoid_last_slot":      1,   # lessons scheduled in last slot
        "weight_teacher_spread":       1,   # gaps in teacher's day (first–last span minus count)
        "weight_subject_daily_spread": 2,   # lessons of same subject clustered on same day
        "weight_heavy_morning":        3,   # heavy subject scheduled after morning_threshold
        "morning_threshold":           4,   # slots > this are considered afternoon
    },
    "heavy_subjects": [],                   # list of subject names marked as heavy
}

DDL = """
CREATE TABLE IF NOT EXISTS problems (
    name TEXT PRIMARY KEY
);
CREATE TABLE IF NOT EXISTS classes (
    problem TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    size    INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (problem, name)
);
CREATE TABLE IF NOT EXISTS subjects (
    problem TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    PRIMARY KEY (problem, name)
);
CREATE TABLE IF NOT EXISTS teachers (
    problem TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    name    TEXT NOT NULL,
    PRIMARY KEY (problem, name)
);
CREATE TABLE IF NOT EXISTS rooms (
    problem   TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    name      TEXT NOT NULL,
    capacity  INTEGER NOT NULL DEFAULT 0,
    room_type TEXT NOT NULL DEFAULT 'standard',
    PRIMARY KEY (problem, name)
);
CREATE TABLE IF NOT EXISTS requirements (
    problem TEXT    NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    class   TEXT    NOT NULL,
    subject TEXT    NOT NULL,
    periods INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (problem, class, subject)
);
CREATE TABLE IF NOT EXISTS can_teach (
    problem TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    teacher TEXT NOT NULL,
    subject TEXT NOT NULL,
    PRIMARY KEY (problem, teacher, subject)
);
CREATE TABLE IF NOT EXISTS subject_room_type (
    problem   TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    subject   TEXT NOT NULL,
    room_type TEXT NOT NULL DEFAULT 'standard',
    PRIMARY KEY (problem, subject)
);
CREATE TABLE IF NOT EXISTS teacher_unavailability (
    problem TEXT    NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    teacher TEXT    NOT NULL,
    day     TEXT    NOT NULL,
    slot    INTEGER NOT NULL,
    PRIMARY KEY (problem, teacher, day, slot)
);
CREATE TABLE IF NOT EXISTS hard_constraints (
    problem                    TEXT    NOT NULL PRIMARY KEY
                               REFERENCES problems(name) ON DELETE CASCADE,
    max_consecutive_same_subj  INTEGER NOT NULL DEFAULT 2,
    max_teacher_periods_day    INTEGER NOT NULL DEFAULT 4
);
CREATE TABLE IF NOT EXISTS soft_constraints (
    problem                    TEXT    NOT NULL PRIMARY KEY
                               REFERENCES problems(name) ON DELETE CASCADE,
    weight_class_holes           INTEGER NOT NULL DEFAULT 1,
    weight_avoid_first_slot      INTEGER NOT NULL DEFAULT 2,
    weight_avoid_last_slot       INTEGER NOT NULL DEFAULT 1,
    weight_teacher_spread        INTEGER NOT NULL DEFAULT 1,
    weight_subject_daily_spread  INTEGER NOT NULL DEFAULT 2,
    weight_heavy_morning         INTEGER NOT NULL DEFAULT 3,
    morning_threshold            INTEGER NOT NULL DEFAULT 4
);
CREATE TABLE IF NOT EXISTS heavy_subjects (
    problem  TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    subject  TEXT NOT NULL,
    PRIMARY KEY (problem, subject)
);
"""


class DB:
    def __init__(self, path=DB_PATH):
        self.path = path
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.executescript(DDL)
        self.conn.commit()
        if DEFAULT_NAME not in self.list():
            self.save(DEFAULT_NAME, DEFAULT_DATA)

    def list(self):
        cur = self.conn.execute("SELECT name FROM problems ORDER BY name")
        return [r[0] for r in cur.fetchall()]

    def load(self, name):
        cur = self.conn.execute("SELECT name FROM problems WHERE name=?", (name,))
        if cur.fetchone() is None:
            raise KeyError(f"Problem '{name}' not found")

        classes = [{"name": r[0], "size": r[1]}
                   for r in self.conn.execute(
                       "SELECT name, size FROM classes WHERE problem=? ORDER BY rowid", (name,))]
        subjects = [r[0] for r in self.conn.execute(
                       "SELECT name FROM subjects WHERE problem=? ORDER BY rowid", (name,))]
        teachers = [r[0] for r in self.conn.execute(
                       "SELECT name FROM teachers WHERE problem=? ORDER BY rowid", (name,))]
        rooms = [{"name": r[0], "capacity": r[1], "room_type": r[2]}
                 for r in self.conn.execute(
                     "SELECT name, capacity, room_type FROM rooms WHERE problem=? ORDER BY rowid",
                     (name,))]

        requirements = {}
        for cls, subj, periods in self.conn.execute(
                "SELECT class, subject, periods FROM requirements WHERE problem=?", (name,)):
            requirements.setdefault(cls, {})[subj] = periods

        can_teach = {}
        for teacher, subj in self.conn.execute(
                "SELECT teacher, subject FROM can_teach WHERE problem=?", (name,)):
            can_teach.setdefault(teacher, []).append(subj)

        subject_room_type = {r[0]: r[1] for r in self.conn.execute(
            "SELECT subject, room_type FROM subject_room_type WHERE problem=?", (name,))}

        teacher_unavailability = [
            {"teacher": r[0], "day": r[1], "slot": r[2]}
            for r in self.conn.execute(
                "SELECT teacher, day, slot FROM teacher_unavailability WHERE problem=?", (name,))
        ]

        hard_row = self.conn.execute(
            "SELECT max_consecutive_same_subj, max_teacher_periods_day "
            "FROM hard_constraints WHERE problem=?", (name,)).fetchone()
        hard_constraints = {
            "max_consecutive_same_subj": hard_row[0] if hard_row else 2,
            "max_teacher_periods_day":   hard_row[1] if hard_row else 4,
        }

        soft_row = self.conn.execute(
            "SELECT weight_class_holes, weight_avoid_first_slot, "
            "weight_avoid_last_slot, weight_teacher_spread, weight_subject_daily_spread, "
            "weight_heavy_morning, morning_threshold "
            "FROM soft_constraints WHERE problem=?", (name,)).fetchone()
        soft_constraints = {
            "weight_class_holes":          soft_row[0] if soft_row else 1,
            "weight_avoid_first_slot":     soft_row[1] if soft_row else 2,
            "weight_avoid_last_slot":      soft_row[2] if soft_row else 1,
            "weight_teacher_spread":       soft_row[3] if soft_row else 1,
            "weight_subject_daily_spread": soft_row[4] if soft_row else 2,
            "weight_heavy_morning":        soft_row[5] if soft_row else 3,
            "morning_threshold":           soft_row[6] if soft_row else 4,
        }

        heavy_subjects = [r[0] for r in self.conn.execute(
            "SELECT subject FROM heavy_subjects WHERE problem=?", (name,)).fetchall()]

        return {
            "classes": classes, "subjects": subjects,
            "teachers": teachers, "rooms": rooms,
            "requirements": requirements, "can_teach": can_teach,
            "subject_room_type": subject_room_type,
            "teacher_unavailability": teacher_unavailability,
            "hard_constraints": hard_constraints,
            "soft_constraints": soft_constraints,
            "heavy_subjects": heavy_subjects,
        }

    def save(self, name, data):
        with self.conn:
            self.conn.execute("DELETE FROM problems WHERE name=?", (name,))
            self.conn.execute("INSERT INTO problems(name) VALUES (?)", (name,))
            self.conn.executemany(
                "INSERT INTO classes(problem,name,size) VALUES (?,?,?)",
                [(name, c["name"], c["size"]) for c in data["classes"]])
            self.conn.executemany(
                "INSERT INTO subjects(problem,name) VALUES (?,?)",
                [(name, s) for s in data["subjects"]])
            self.conn.executemany(
                "INSERT INTO teachers(problem,name) VALUES (?,?)",
                [(name, t) for t in data["teachers"]])
            self.conn.executemany(
                "INSERT INTO rooms(problem,name,capacity,room_type) VALUES (?,?,?,?)",
                [(name, r["name"], r["capacity"], r.get("room_type", "standard"))
                 for r in data["rooms"]])
            rows = [(name, cls, subj, cnt)
                    for cls, sv in data["requirements"].items()
                    for subj, cnt in sv.items() if int(cnt) > 0]
            self.conn.executemany(
                "INSERT INTO requirements(problem,class,subject,periods) VALUES (?,?,?,?)", rows)
            ct_rows = [(name, teacher, subj)
                       for teacher, subjects in data["can_teach"].items()
                       for subj in subjects]
            self.conn.executemany(
                "INSERT INTO can_teach(problem,teacher,subject) VALUES (?,?,?)", ct_rows)
            srt = data.get("subject_room_type", {})
            self.conn.executemany(
                "INSERT INTO subject_room_type(problem,subject,room_type) VALUES (?,?,?)",
                [(name, subj, rtype) for subj, rtype in srt.items()])
            unavail = data.get("teacher_unavailability", [])
            self.conn.executemany(
                "INSERT INTO teacher_unavailability(problem,teacher,day,slot) VALUES (?,?,?,?)",
                [(name, u["teacher"], u["day"], u["slot"]) for u in unavail])
            hard = data.get("hard_constraints", {})
            self.conn.execute(
                "INSERT INTO hard_constraints(problem,max_consecutive_same_subj,max_teacher_periods_day)"
                " VALUES (?,?,?)",
                (name,
                 int(hard.get("max_consecutive_same_subj", 2)),
                 int(hard.get("max_teacher_periods_day", 4))))
            soft = data.get("soft_constraints", {})
            self.conn.execute(
                "INSERT INTO soft_constraints(problem,weight_class_holes,weight_avoid_first_slot,"
                "weight_avoid_last_slot,weight_teacher_spread,weight_subject_daily_spread,"
                "weight_heavy_morning,morning_threshold) VALUES (?,?,?,?,?,?,?,?)",
                (name,
                 int(soft.get("weight_class_holes", 1)),
                 int(soft.get("weight_avoid_first_slot", 2)),
                 int(soft.get("weight_avoid_last_slot", 1)),
                 int(soft.get("weight_teacher_spread", 1)),
                 int(soft.get("weight_subject_daily_spread", 2)),
                 int(soft.get("weight_heavy_morning", 3)),
                 int(soft.get("morning_threshold", 4))))
            for s in data.get("heavy_subjects", []):
                self.conn.execute(
                    "INSERT OR IGNORE INTO heavy_subjects(problem,subject) VALUES (?,?)", (name, s))

    def delete(self, name):
        if name == DEFAULT_NAME:
            raise ValueError("Cannot delete the DEFAULT problem")
        with self.conn:
            self.conn.execute("DELETE FROM problems WHERE name=?", (name,))


if __name__ == "__main__":
    import os
    # Fresh DB for testing
    test_path = "/tmp/timetable_test.db"
    if os.path.exists(test_path):
        os.remove(test_path)
    db = DB(test_path)
    print("Problems:", db.list())
    d = db.load(DEFAULT_NAME)
    print("Classes:", [c["name"] for c in d["classes"]])
    print("Rooms:", [(r["name"], r["room_type"]) for r in d["rooms"]])
    print("Subject room types:", d["subject_room_type"])
    print("Soft constraints:", d["soft_constraints"])
    # Round-trip test
    db.save("Test", d)
    d2 = db.load("Test")
    assert d2["subject_room_type"] == d["subject_room_type"], "subject_room_type mismatch"
    assert d2["soft_constraints"] == d["soft_constraints"], "soft_constraints mismatch"
    print("Round-trip OK")
