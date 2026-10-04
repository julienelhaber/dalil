"""Measure the box reader on real photos. Run: python -m scripts.eval_photos"""
import time
from pathlib import Path

from app.photo import number, read_box

BOXES = Path(__file__).resolve().parent.parent / "data" / "boxes"

# Photo file -> (brand, strength in mg) printed on the box, or None for a photo with no box
EXPECTED = {
    "flumivir.jpg": ("FLUMIVIR", 75),
    "exonar.jpg": ("EXONAR", 40),
    "gastrimut.jpg": ("GASTRIMUT", 20),
    "rapidus.jpg": ("RAPIDUS", 50),
    "plenica.jpg": ("PLENICA", 25),
    "not_a_box.jpg": None,
}


def main():
    correct = 0
    for name, expected in EXPECTED.items():
        start = time.perf_counter()
        drug = read_box((BOXES / name).read_bytes())
        seconds = time.perf_counter() - start
        if expected is None:
            ok = drug is None
        else:
            ok = drug is not None and drug["brand_name"] == expected[0] \
                and number(drug["strength"]) == expected[1]
        correct += ok
        found = f"{drug['brand_name']} {drug['strength']}" if drug else "not sure"
        print(f"{name:15} {found:22} {seconds:5.2f} s  {'OK' if ok else 'WRONG'}")
    print(f"{correct}/{len(EXPECTED)} correct")


if __name__ == "__main__":
    main()
