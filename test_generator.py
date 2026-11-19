#!/usr/bin/env python3
"""
Matndan test tuzuvchi dastur.

Faqat standart kutubxonadan foydalanadi, qo'shimcha o'rnatish shart emas.

Misol:
    python test_generator.py matn.txt --grade 5 --count 10
    python test_generator.py matn.txt --grade 9 --count 20 --level qiyin --seed 42
"""

import argparse
import random
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# So'z qismi: harflar, o'zbekcha apostrof (o', g', ʻ, ʼ, ’) bilan birga
WORD_RE = re.compile(r"[^\W\d_]+(?:['ʻʼ’][^\W\d_]+)*")

# Savol uchun tanlanmaydigan, juda ko'p uchraydigan so'zlar
STOP = {
    "va", "bu", "u", "bilan", "uchun", "ham", "lekin", "edi", "emas", "deb",
    "da", "ga", "ni", "ning", "bir", "shu", "yoki", "esa", "kabi", "har",
    "juda", "o'sha", "ular", "biz", "siz", "men", "sen", "ekan", "qilib",
    "bo'lib", "bo'lgan", "bo'lsa", "keyin", "shunday", "hech", "qanday",
}

# Daraja sozlamalari
#   min_len   - tanlanadigan so'zning eng kam uzunligi
#   min_words - gap eng kam so'z soni
#   max_words - gap eng ko'p so'z soni
#   len_diff  - chalg'ituvchi so'z uzunligidan farqi (kichik bo'lsa qiyinroq)
LEVELS = {
    "oson":  {"min_len": 4, "min_words": 5,  "max_words": 16, "len_diff": 3},
    "orta":  {"min_len": 5, "min_words": 7,  "max_words": 30, "len_diff": 2},
    "qiyin": {"min_len": 7, "min_words": 12, "max_words": 60, "len_diff": 1},
}

LEVEL_NAMES = {"oson": "Oson", "orta": "O'rta", "qiyin": "Qiyin"}
LETTERS = ["A", "B", "C", "D"]


@dataclass
class Question:
    text: str
    options: list
    correct: int  # to'g'ri variant indeksi (0..3)


def level_for_grade(grade: int) -> str:
    if grade <= 3:
        return "oson"
    if grade <= 6:
        return "orta"
    return "qiyin"


def core_of(token: str) -> str:
    """Tinish belgilarisiz so'z qismini qaytaradi."""
    m = WORD_RE.search(token)
    return m.group(0) if m else ""


def split_sentences(text: str) -> list:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if p.strip()]


def build_pool(text: str) -> list:
    """Chalg'ituvchi variantlar uchun matndagi noyob so'zlar."""
    seen = {}
    for w in WORD_RE.findall(text):
        key = w.lower()
        if len(w) >= 3 and key not in STOP and key not in seen:
            seen[key] = w
    return list(seen.values())


def generate(text: str, level: str, count: int, rng: random.Random) -> list:
    cfg = LEVELS[level]

    sentences = [
        s for s in split_sentences(text)
        if cfg["min_words"] <= len(s.split()) <= cfg["max_words"]
    ]
    rng.shuffle(sentences)

    pool = build_pool(text)
    questions = []
    used_answers = set()

    for sentence in sentences:
        if len(questions) >= count:
            break

        tokens = sentence.split()

        candidates = []
        for idx, tok in enumerate(tokens):
            c = core_of(tok)
            if (len(c) >= cfg["min_len"]
                    and c.lower() not in STOP
                    and c.lower() not in used_answers):
                candidates.append((idx, c))
        if not candidates:
            continue

        idx, answer = rng.choice(candidates)

        distractor_pool = [
            w for w in pool
            if w.lower() != answer.lower()
            and abs(len(w) - len(answer)) <= cfg["len_diff"] + 1
        ]
        rng.shuffle(distractor_pool)

        distractors = []
        seen = {answer.lower()}
        for w in distractor_pool:
            if w.lower() not in seen:
                seen.add(w.lower())
                distractors.append(w)
                if len(distractors) == 3:
                    break
        if len(distractors) < 3:
            continue

        used_answers.add(answer.lower())
        tokens[idx] = tokens[idx].replace(answer, "_____", 1)

        options = [answer] + distractors
        rng.shuffle(options)
        questions.append(Question(
            text=" ".join(tokens),
            options=options,
            correct=options.index(answer),
        ))

    return questions


def render_test(questions, grade, level, title_source) -> str:
    lines = []
    lines.append(f"{grade}-sinf. Matn bo'yicha test ({LEVEL_NAMES[level]})")
    lines.append(f"Manba: {title_source}")
    lines.append("")
    lines.append("Ism: ______________________     Sana: ____________")
    lines.append("")
    for i, q in enumerate(questions, 1):
        lines.append(f"{i}. {q.text}")
        for j, opt in enumerate(q.options):
            lines.append(f"   {LETTERS[j]}) {opt}")
        lines.append("")
    return "\n".join(lines)


def render_answers(questions) -> str:
    items = [f"{i}-{LETTERS[q.correct]}" for i, q in enumerate(questions, 1)]
    return "Javoblar kaliti:\n" + ", ".join(items) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Matndan test tuzish")
    parser.add_argument("source", help="Matn fayli (.txt)")
    parser.add_argument("--grade", type=int, required=True, choices=range(1, 12),
                        metavar="{1..11}", help="Sinf (1-11)")
    parser.add_argument("--count", type=int, default=10,
                        choices=[10, 15, 20, 25, 30, 35, 40, 45, 50],
                        help="Savollar soni")
    parser.add_argument("--level", choices=list(LEVELS), default=None,
                        help="Daraja (berilmasa, sinfga qarab avtomatik)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Tasodifiylik uchun raqam (bir xil test olish uchun)")
    parser.add_argument("--out", default="natija", help="Chiqish papkasi")
    args = parser.parse_args()

    src = Path(args.source)
    if not src.exists():
        sys.exit(f"Xato: '{src}' fayli topilmadi.")

    text = src.read_text(encoding="utf-8").strip()
    if len(text) < 200:
        sys.exit("Xato: matn kamida 200 belgidan iborat bo'lishi kerak.")

    level = args.level or level_for_grade(args.grade)
    rng = random.Random(args.seed)

    questions = generate(text, level, args.count, rng)
    if not questions:
        sys.exit("Bu matndan savol tuzib bo'lmadi. Matnni uzunroq qiling "
                 "yoki boshqa daraja tanlang.")
    if len(questions) < args.count:
        print(f"Ogohlantirish: {args.count} ta o'rniga {len(questions)} ta savol tuzildi "
              f"(matn yetarli emas).")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = src.stem

    test_path = out_dir / f"{stem}_test.txt"
    key_path = out_dir / f"{stem}_javoblar.txt"

    test_path.write_text(render_test(questions, args.grade, level, src.name),
                         encoding="utf-8")
    key_path.write_text(render_answers(questions), encoding="utf-8")

    print(f"Test saqlandi: {test_path}")
    print(f"Javoblar kaliti saqlandi: {key_path}")


if __name__ == "__main__":
    main()
