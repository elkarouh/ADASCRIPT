import pytest
from math import sqrt, isclose, cos, radians
from hek_map_utils import (
    Vector, Position, GeoVector, GeoPoint,
    dms2dec, dd2dms, human2dec_degree, human_latlong2dec, dec2human_latlong,
)


# ──────────────────────────────────────────────
# Coordinate conversion functions
# ──────────────────────────────────────────────

class TestDms2Dec:
    def test_latitude_north(self):
        # 50°54'05"N → ~50.9014
        result = dms2dec("505405N")
        assert isclose(result, 50.90138, abs_tol=0.001)

    def test_latitude_south(self):
        result = dms2dec("505405S")
        assert result < 0
        assert isclose(result, -50.90138, abs_tol=0.001)

    def test_longitude_east(self):
        # 004°29'04"E
        result = dms2dec("0042904E", is_longitude=True)
        assert result > 0
        assert isclose(result, 4.4844, abs_tol=0.001)

    def test_longitude_west(self):
        result = dms2dec("0042904W", is_longitude=True)
        assert result < 0

    def test_with_subsecond_digits(self):
        # Position string with extra digits (no decimal point)
        result = dms2dec("08415400S")
        assert result < 0


class TestDd2Dms:
    def test_positive_latitude(self):
        result = dd2dms(50.9014, "NS")
        assert result.endswith("N")
        assert result.startswith("50")

    def test_negative_latitude(self):
        result = dd2dms(-33.86, "NS")
        assert result.endswith("S")

    def test_positive_longitude(self):
        result = dd2dms(4.484, "EW")
        assert result.endswith("E")
        # longitude has 3-digit degrees
        assert len(result.split("E")[0]) >= 7

    def test_negative_longitude(self):
        result = dd2dms(-12.034, "EW")
        assert result.endswith("W")


class TestHuman2DecDegree:
    def test_bearing(self):
        # 306°52'05.37"
        result = human2dec_degree("3065205.37")
        assert isclose(result, 306.868, abs_tol=0.01)


class TestHumanLatlongRoundtrip:
    def test_roundtrip(self):
        original = "505405N 0042904E"
        lat, lon = human_latlong2dec(original)
        back = dec2human_latlong(lat, lon)
        lat2, lon2 = human_latlong2dec(back)
        assert isclose(lat, lat2, abs_tol=0.01)
        assert isclose(lon, lon2, abs_tol=0.01)


# ──────────────────────────────────────────────
# Vector class
# ──────────────────────────────────────────────

class TestVector:
    def test_construction(self):
        v = Vector(10, 0)
        assert isclose(v.length, 10, abs_tol=1e-9)
        assert isclose(v.angle, 0, abs_tol=1e-9)

    def test_xy_components(self):
        v = Vector(10, 0)  # pointing along x-axis
        assert isclose(v.x, 10, abs_tol=1e-9)
        assert isclose(v.y, 0, abs_tol=1e-6)

    def test_rotated_by(self):
        v = Vector(1, 0)
        rotated = v.rotated_by(90)
        assert isclose(rotated.angle, 90, abs_tol=1e-9)
        assert isclose(rotated.length, 1, abs_tol=1e-9)

    def test_shortened_by(self):
        v = Vector(10, 45)
        shorter = v.shortened_by(3)
        assert isclose(shorter.length, 7, abs_tol=1e-9)
        assert isclose(shorter.angle, 45, abs_tol=1e-9)

    def test_dot_product_perpendicular(self):
        v1 = Vector(1, 0)
        v2 = Vector(1, 90)
        assert isclose(v1.dot_product(v2), 0, abs_tol=1e-9)

    def test_dot_product_parallel(self):
        v1 = Vector(3, 0)
        v2 = Vector(4, 0)
        assert isclose(v1.dot_product(v2), 12, abs_tol=1e-9)

    def test_cross_product(self):
        v1 = Vector(1, 0)
        v2 = Vector(1, 90)
        # cross product of unit vectors at 90° should be 1
        assert isclose(v1.cross(v2), 1, abs_tol=1e-9)

    def test_cos_theta_same_direction(self):
        v1 = Vector(5, 30)
        v2 = Vector(3, 30)
        assert isclose(v1.cos_theta(v2), 1.0, abs_tol=1e-9)

    def test_cos_theta_perpendicular(self):
        v1 = Vector(1, 0)
        v2 = Vector(1, 90)
        assert isclose(v1.cos_theta(v2), 0, abs_tol=1e-9)

    def test_cos_theta_opposite(self):
        v1 = Vector(1, 0)
        v2 = Vector(1, 180)
        assert isclose(v1.cos_theta(v2), -1.0, abs_tol=1e-9)

    def test_unit_vector(self):
        v = Vector(5, 30)
        u = v.unit()
        assert isclose(abs(u), 1.0, abs_tol=1e-9)

    def test_projection(self):
        v = Vector(5, 45)
        axis = Vector(1, 0)
        proj = v.projection(axis)
        # projection of 45° vector onto x-axis
        assert isclose(abs(proj), 5 * cos(radians(45)), abs_tol=1e-6)

    def test_add_no_print(self, capsys):
        v1 = Vector(3, 0)
        v2 = Vector(4, 0)
        result = v1 + v2
        captured = capsys.readouterr()
        assert captured.out == ""  # no debug print output
        assert isclose(result.length, 7, abs_tol=1e-6)

    def test_sub_no_print(self, capsys):
        v1 = Vector(7, 0)
        v2 = Vector(3, 0)
        result = v1 - v2
        captured = capsys.readouterr()
        assert captured.out == ""  # no debug print output
        assert isclose(result.length, 4, abs_tol=1e-6)

    def test_mul(self):
        v = Vector(3, 45)
        scaled = v * 2
        assert isclose(scaled.length, 6, abs_tol=1e-9)
        assert isclose(scaled.angle, 45, abs_tol=1e-9)

    def test_str(self):
        v = Vector(10, 45)
        s = str(v)
        assert "m" in s
        assert "degrees" in s

    def test_triangle_area(self):
        v1 = Vector(3, 0)
        v2 = Vector(4, 90)
        assert isclose(v1.triangle_area(v2), 6.0, abs_tol=1e-9)


# ──────────────────────────────────────────────
# Position class
# ──────────────────────────────────────────────

class TestPosition:
    def test_construction(self):
        p = Position(3, 4)
        assert p.x == 3
        assert p.y == 4

    def test_is_tuple(self):
        p = Position(1, 2)
        assert p[0] == 1
        assert p[1] == 2

    def test_add_returns_position(self):
        p = Position(1, 2)
        v = Vector(1, 0)  # unit vector along x
        result = p + v
        assert isinstance(result, Position)

    def test_add_values(self):
        p = Position(1, 0)
        v = Vector(1, 0)  # 1 unit along x-axis
        result = p + v
        assert isclose(result.x, 2.0, abs_tol=1e-6)
        assert isclose(result.y, 0.0, abs_tol=1e-6)

    def test_sub_returns_vector(self):
        p1 = Position(5, 5)
        p2 = Position(2, 1)
        result = p1 - p2
        assert isinstance(result, Vector)

    def test_rotate_around_point(self):
        p1 = Position(2, 0)
        origin = Position(0, 0)
        rotated = p1.rotate_around_point(origin, 90)
        assert isinstance(rotated, Position)
        assert isclose(rotated.x, 0, abs_tol=1e-6)
        assert isclose(rotated.y, 2, abs_tol=1e-6)


# ──────────────────────────────────────────────
# GeoVector class
# ──────────────────────────────────────────────

class TestGeoVector:
    def test_construction(self):
        gv = GeoVector(100, 45)
        assert isclose(gv.magnitude, 100, abs_tol=1e-6)
        assert isclose(gv.phase, 45, abs_tol=1e-6)

    def test_turn(self):
        gv = GeoVector(50, 90)
        turned = gv.turn(45)
        assert isclose(turned.magnitude, 50, abs_tol=1e-6)
        assert isclose(turned.phase, 135, abs_tol=1e-6)

    def test_dot_product(self):
        gv1 = GeoVector(1, 0)
        gv2 = GeoVector(1, 90)
        assert isclose(gv1.dot_product(gv2), 0, abs_tol=1)

    def test_cross_product(self):
        gv1 = GeoVector(1, 0)
        gv2 = GeoVector(1, 90)
        result = gv1.cross_product(gv2)
        assert result is not None  # was empty body before fix
        assert isinstance(result, float)

    def test_str(self):
        gv = GeoVector(100, 45)
        s = str(gv)
        assert "km" in s
        assert "degrees" in s


# ──────────────────────────────────────────────
# GeoPoint class
# ──────────────────────────────────────────────

class TestGeoPoint:
    def test_construction(self):
        p = GeoPoint(50.9, 4.48)
        assert isclose(p.latitude, 50.9, abs_tol=1e-9)
        assert isclose(p.longitude, 4.48, abs_tol=1e-9)

    def test_is_tuple(self):
        p = GeoPoint(50.9, 4.48)
        assert p[0] == p.latitude
        assert p[1] == p.longitude

    def test_construct_from_dms(self):
        p = GeoPoint.construct("505405N 0042904E")
        assert isclose(p.latitude, 50.9014, abs_tol=0.01)
        assert isclose(p.longitude, 4.4844, abs_tol=0.01)

    def test_add_geovector(self):
        p = GeoPoint(50.0, 4.0)
        v = GeoVector(100, 0)  # 100km north
        result = p + v
        assert isinstance(result, GeoPoint)
        assert result.latitude > p.latitude  # should be further north

    def test_sub_geopoints(self):
        p1 = GeoPoint(51.0, 4.0)
        p2 = GeoPoint(50.0, 4.0)
        result = p1 - p2
        assert isinstance(result, GeoVector)
        assert result.magnitude > 0  # ~111 km

    def test_format_human(self):
        p = GeoPoint(50.9014, 4.4844)
        result = f"{p:h}"
        assert "N" in result
        assert "E" in result

    def test_format_decimal(self):
        p = GeoPoint(50.9014, 4.4844)
        result = f"{p:d}"
        assert "[" in result and "]" in result

    def test_format_default(self):
        p = GeoPoint(50.9014, 4.4844)
        result = f"{p}"
        assert "N" in result  # includes human-readable
        assert "[" in result  # includes decimal

    def test_rotate_around_point(self):
        p1 = GeoPoint(51.0, 4.0)
        center = GeoPoint(50.0, 4.0)
        rotated = p1.rotate_around_point(center, 180)
        assert isinstance(rotated, GeoPoint)
        # 180° rotation: should end up roughly south of center
        assert rotated.latitude < center.latitude

    def test_is_point_inside_triangle_inside(self):
        A = GeoPoint(50.0, 3.0)
        B = GeoPoint(51.0, 3.0)
        C = GeoPoint(50.5, 5.0)
        inside = GeoPoint(50.5, 3.5)
        assert inside.is_point_inside_triangle(A, B, C)

    def test_is_point_inside_triangle_outside(self):
        A = GeoPoint(50.0, 3.0)
        B = GeoPoint(51.0, 3.0)
        C = GeoPoint(50.5, 5.0)
        outside = GeoPoint(52.0, 6.0)
        assert not outside.is_point_inside_triangle(A, B, C)

    def test_is_point_inside_triangle_degenerate(self):
        # All three vertices on same line → degenerate triangle
        A = GeoPoint(50.0, 3.0)
        B = GeoPoint(51.0, 3.0)
        C = GeoPoint(52.0, 3.0)
        point = GeoPoint(50.5, 3.0)
        # Should return False without ZeroDivisionError
        assert not point.is_point_inside_triangle(A, B, C)

    def test_is_point_inside_polygon_inside(self):
        # Simple square polygon
        poly = [
            GeoPoint(50.0, 3.0),
            GeoPoint(51.0, 3.0),
            GeoPoint(51.0, 5.0),
            GeoPoint(50.0, 5.0),
        ]
        inside = GeoPoint(50.5, 4.0)
        assert inside.is_point_inside_polygon(poly)

    def test_is_point_inside_polygon_outside(self):
        poly = [
            GeoPoint(50.0, 3.0),
            GeoPoint(51.0, 3.0),
            GeoPoint(51.0, 5.0),
            GeoPoint(50.0, 5.0),
        ]
        outside = GeoPoint(52.0, 6.0)
        assert not outside.is_point_inside_polygon(poly)

    def test_is_point_inside_polygon_horizontal_edge(self):
        # Polygon with a horizontal edge (y1 == y2) → was division by zero
        poly = [
            GeoPoint(50.0, 3.0),
            GeoPoint(51.0, 3.0),  # horizontal edge (same longitude 3.0)
            GeoPoint(51.0, 5.0),
            GeoPoint(50.0, 5.0),
        ]
        point = GeoPoint(50.5, 3.0)
        # Should not raise ZeroDivisionError
        result = point.is_point_inside_polygon(poly)
        assert isinstance(result, bool)

    def test_construct_from_name(self):
        p = GeoPoint.construct_from_name("EBBR")
        assert isinstance(p, GeoPoint)
        # Brussels is roughly at 50.9°N, 4.5°E
        assert 50 < p.latitude < 52
        assert 3 < p.longitude < 6
