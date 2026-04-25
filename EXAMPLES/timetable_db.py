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
  rooms(problem TEXT, name TEXT, capacity INTEGER)
  requirements(problem TEXT, class TEXT, subject TEXT, periods INTEGER)
  can_teach(problem TEXT, teacher TEXT, subject TEXT)

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
        {"name": "R01", "capacity": 32},
        {"name": "R02", "capacity": 32},
        {"name": "R03", "capacity": 32},
        {"name": "R04", "capacity": 32},
        {"name": "Lab1", "capacity": 30},
        {"name": "Lab2", "capacity": 30},
        {"name": "Gym",  "capacity": 60},
        {"name": "ArtRm","capacity": 28},
    ],
    "requirements": {
        "Year7A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year7B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year8A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year8B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year9A": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
        "Year9B": {"Math":4,"English":4,"Science":3,"History":2,"Geography":2,"French":2,"PE":2,"Art":1},
    },
    "can_teach": {
        "Adams":  ["Math", "Science"],
        "Brown":  ["English", "History"],
        "Clarke": ["Math", "French"],
        "Davies": ["Science", "Geography"],
        "Evans":  ["English", "Art"],
        "Foster": ["History", "Geography"],
        "Green":  ["Math", "Science"],
        "Harris": ["PE"],
        "Ito":    ["French", "Art"],
        "Jones":  ["English", "PE"],
    },
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
    problem  TEXT NOT NULL REFERENCES problems(name) ON DELETE CASCADE,
    name     TEXT NOT NULL,
    capacity INTEGER NOT NULL DEFAULT 0,
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
        rooms = [{"name": r[0], "capacity": r[1]}
                 for r in self.conn.execute(
                     "SELECT name, capacity FROM rooms WHERE problem=? ORDER BY rowid", (name,))]

        requirements = {}
        for cls, subj, periods in self.conn.execute(
                "SELECT class, subject, periods FROM requirements WHERE problem=?", (name,)):
            requirements.setdefault(cls, {})[subj] = periods

        can_teach = {}
        for teacher, subj in self.conn.execute(
                "SELECT teacher, subject FROM can_teach WHERE problem=?", (name,)):
            can_teach.setdefault(teacher, []).append(subj)

        return {
            "classes": classes, "subjects": subjects,
            "teachers": teachers, "rooms": rooms,
            "requirements": requirements, "can_teach": can_teach,
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
                "INSERT INTO rooms(problem,name,capacity) VALUES (?,?,?)",
                [(name, r["name"], r["capacity"]) for r in data["rooms"]])
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

    def delete(self, name):
        if name == DEFAULT_NAME:
            raise ValueError("Cannot delete the DEFAULT problem")
        with self.conn:
            self.conn.execute("DELETE FROM problems WHERE name=?", (name,))


if __name__ == "__main__":
    db = DB()
    print("Problems:", db.list())
    d = db.load(DEFAULT_NAME)
    print("Classes:", [c["name"] for c in d["classes"]])
    print("Requirements:", d["requirements"])
