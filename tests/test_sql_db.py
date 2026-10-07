from src.sql_db import get_lot_by_name, list_lots, seed_db, update_availability


def test_seed_db_creates_three_lots(tmp_path):
    db_path = str(tmp_path / "test.db")
    seed_db(db_path=db_path)
    lots = list_lots(db_path=db_path)
    assert len(lots) == 3
    assert "Downtown Garage" in {l.name for l in lots}


def test_seed_db_is_idempotent(tmp_path):
    db_path = str(tmp_path / "test.db")
    seed_db(db_path=db_path)
    seed_db(db_path=db_path)  # calling twice should not duplicate rows
    assert len(list_lots(db_path=db_path)) == 3


def test_get_lot_by_name_case_insensitive(tmp_path):
    db_path = str(tmp_path / "test.db")
    seed_db(db_path=db_path)
    lot = get_lot_by_name("downtown", db_path=db_path)
    assert lot is not None
    assert lot.name == "Downtown Garage"


def test_update_availability_never_goes_negative(tmp_path):
    db_path = str(tmp_path / "test.db")
    seed_db(db_path=db_path)
    update_availability("Downtown Garage", -10000, db_path=db_path)
    lot = get_lot_by_name("Downtown Garage", db_path=db_path)
    assert lot.available_slots == 0