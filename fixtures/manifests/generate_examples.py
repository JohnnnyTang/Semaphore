"""Regenerate authored W2 manifest examples; never generates model results."""

import copy
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Original synthetic labels/clues, authored for structural examples; not playtested.
WORDS = """apple|orchard fruit|crisp snack|cider ingredient
anchor|ship weight|hold a vessel still|heavy seabed hook
balloon|floating party decoration|helium toy|inflatable sphere
basket|woven container|picnic carrier|wicker storage
bell|ringing metal|church chime|school signal
blanket|warm bed covering|cozy layer|picnic spread
bridge|river crossing|road over water|connect two banks
broom|sweeping tool|bristled floor cleaner|witch transport
bucket|water carrier|pail|open topped container
candle|wax light|birthday flame|wick and glow
carrot|orange root|rabbit snack|crunchy garden vegetable
castle|fortified home|royal fortress|towers and moat
chair|single seat|sit down|furniture with legs
clock|time display|ticking dial|hours and minutes
cloud|sky vapor|rain source|fluffy overhead shape
compass|direction finder|magnetic needle|north pointer
crown|royal headwear|monarch symbol|jeweled circle
drum|percussion instrument|beat maker|taut musical skin
feather|bird covering|light plume|quill material
fork|pronged utensil|dinner tool|spear a bite
glacier|slow river of ice|frozen mountain flow|crevasse landscape
guitar|strummed strings|six string instrument|acoustic music
hammer|nail driver|striking tool|carpenter mallet
helmet|protective headwear|cycling safety gear|hard shell cap
island|land surrounded by water|isolated shore|ocean landmass
key|lock opener|small toothed metal|door access tool
ladder|climbing rungs|reach the roof|portable steps
lantern|portable light|camping glow|enclosed flame
lemon|sour yellow fruit|citrus wedge|tart juice
mirror|reflective glass|see your face|silvered surface
needle|sewing point|thread guide|tiny sharp tool
oven|baking chamber|kitchen heat box|roast dinner appliance
pencil|erasable writing tool|graphite stick|school drawing tool
pillow|head cushion|soft bed support|stuffed sleeping comfort
rope|twisted cord|tie a knot|climbing line
shell|mollusk covering|spiral beach treasure|hard sea casing
spoon|soup utensil|rounded eating tool|scoop a bite
tent|camping shelter|fabric outdoor home|pegs and poles
umbrella|rain shield|folding canopy|portable weather cover
wheel|rolling circle|axle companion|round transport part"""


def write(name: str, value: object) -> None:
    (HERE / name).write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> None:
    rows = [line.split("|") for line in WORDS.splitlines()]
    pack = {
        "spec_version": "1-draft-w2",
        "pack": {
            "id": "everyday-fixture",
            "name": "Everyday fixture",
            "version": "1.0.0",
            "author": "Semaphore synthetic fixture",
            "description": "Authored schema/hygiene examples; no measured playability claim.",
            "tags": ["synthetic"],
            "language": "en",
            "license": "MIT; original fixture text authored for this repository",
        },
        "entries": [{"id": row[0], "text": row[0]} for row in rows],
        "test_set": {row[0]: row[1:] for row in rows},
        "provenance": {"agent": "synthetic W2-D fixture; no model evaluation performed"},
    }
    write("valid-structural.json", pack)
    cases = [{"file": "valid-structural.json", "expected": "ok"}]
    mutations = {
        "uploaded-vectors": ("schema_invalid", lambda p: p.update(vectors=[[0.1, 0.2]])),
        "missing-license": ("schema_invalid", lambda p: p["pack"].pop("license")),
        "duplicate-label": (
            "duplicate_entry",
            lambda p: p["entries"][1].update(text="  APPLE  "),
        ),
        "foreign-test-id": (
            "test_coverage",
            lambda p: p["test_set"].update(foreign=p["test_set"].pop("apple")),
        ),
        "duplicate-normalized-clue": (
            "duplicate_clue",
            lambda p: p["test_set"]["apple"].__setitem__(1, " ORCHARD   FRUIT "),
        ),
    }
    for name, (expected, mutate) in mutations.items():
        invalid = copy.deepcopy(pack)
        mutate(invalid)
        filename = "invalid-" + name + ".json"
        write(filename, invalid)
        cases.append({"file": filename, "expected": expected})
    illustrative = {
        "spec_version": "1",
        "pack": {
            "id": "physical-geography-101",
            "name": "Physical Geography 101",
            "version": "1.0.0",
            "author": "nickname",
            "description": "Landforms and processes",
            "tags": ["geography"],
            "language": "en",
            "license": "CC-BY-4.0",
        },
        "entries": [
            {"text": "glacier", "forbidden_clues": ["glacial"], "tier": 1},
            {"text": "oxbow lake", "embed_text": "oxbow lake, a cut-off river meander", "tier": 2},
        ],
        "test_set": {"glacier": ["slow river of ice", "ice age", "crevasse"]},
        "test_report": {"reachability": 0.94, "mean_rank": 1.6, "flagged": ["loess"]},
        "provenance": {
            "agent": "self-reported string",
            "packtool": "0.1.0",
            "embedding_model": "<id>@<revision>",
        },
    }
    write("invalid-handoff-illustration.json", illustrative)
    cases.append({"file": "invalid-handoff-illustration.json", "expected": "schema_invalid"})
    write(
        "cases.json",
        {"fixture_version": "draft-w2", "schema": "manifest.schema.json", "cases": cases},
    )


if __name__ == "__main__":
    main()
