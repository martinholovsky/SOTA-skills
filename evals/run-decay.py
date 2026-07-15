#!/usr/bin/env python3
"""Skill-application DECAY over a long session — does the model stop applying a
rule loaded early as the conversation grows, and does a per-prompt reminder fix it?

Every other eval measures a SINGLE call. This one measures the TEMPORAL effect the
literature warns about (Laban et al., "LLMs Get Lost in Multi-Turn Conversation";
instruction adherence drops with turn count) and that SOTA's optional
`UserPromptSubmit` reminder hook exists to counter. It is roadmap item 5.

Method (clean, raw OpenRouter API, blind judge):
  - Build a multi-turn `messages` conversation: the engineering guidance is
    established at TURN 1 ("apply this to everything you build this session"),
    followed by K turns of UNRELATED filler Q&A (grows context without
    reinforcing the guidance), then a final build task (the probe).
  - Arms:
      * anchor   — guidance at turn 1 only (measures decay as K grows).
      * reminder — guidance at turn 1 PLUS a short, generic "remember the guidance
        from the start" line on the probe turn (the analog of SOTA's per-prompt
        reminder hook; names no specific concern, so no rubric leakage).
      * control  — no guidance at all (baseline).
  - Depths: K in {0, 12, 30} filler turns.
  - The blind opus judge scores the probe artifact against the task's completeness
    rubric. DECAY = anchor@K0 - anchor@Kmax. REMINDER RECOVERY = reminder@Kmax -
    anchor@Kmax.

Auth: OPENROUTER_API_KEY (env or ./.env). Never printed/committed.
Usage: python3 evals/run-decay.py [--task c6_webhook] [--depths 0,12,30]
       [--build-model M] [--judge-model M] [--out FILE]
"""
import argparse
import json
import os
import sys
import importlib.util
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "run_completeness", os.path.join(ROOT, "evals/run-completeness.py"))
_rc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc)

# Generic, OFF-TOPIC filler exchanges with substantial (paragraph) answers — they
# grow the intervening context and turn count WITHOUT reinforcing the engineering
# guidance (no coding, no "be thorough" cues). Answers are ~4-6 sentences so the
# guidance is meaningfully diluted and pushed back as K grows.
FILLER = [
    ("Tell me about the history of the Roman aqueducts.",
     "Roman aqueducts were gravity-fed channels that carried water from distant springs into cities, some running over 90 kilometers. Engineers maintained a precise, nearly imperceptible downward gradient across the whole route. Where valleys interrupted the path, they built tiered stone arches to keep the channel level. The water fed public fountains, baths, and some private homes. Many aqueducts remained in use for centuries, and a few sections still stand today."),
    ("How does the water cycle work?",
     "The water cycle moves water continuously between the surface and the atmosphere. Solar heat evaporates water from oceans, lakes, and rivers into vapor. That vapor rises, cools, and condenses into clouds. When droplets grow heavy enough they fall as precipitation. The water then flows over land or soaks into the ground, eventually returning to the oceans to begin again."),
    ("Explain the basic rules of chess for a beginner.",
     "Chess is played on an eight-by-eight board between two sides, white and black. Each side has a king, a queen, two rooks, two bishops, two knights, and eight pawns, each moving in its own way. The goal is checkmate: attacking the enemy king so it cannot escape capture. Players alternate turns moving one piece at a time. Special moves include castling, en passant, and promoting a pawn that reaches the far side."),
    ("What caused the extinction of the dinosaurs?",
     "The leading explanation is a massive asteroid impact about sixty-six million years ago near what is now the Yucatan Peninsula. The collision threw enormous amounts of dust and debris into the atmosphere, blocking sunlight for a long period. Reduced light collapsed plant growth and the food chains that depended on it. Widespread wildfires and climate disruption followed. Non-avian dinosaurs died out, while birds and small mammals survived."),
    ("Describe how a rainbow forms.",
     "A rainbow forms when sunlight passes through raindrops in the air. Each drop refracts the light as it enters, reflects it off the back surface, and refracts it again on the way out. Different wavelengths bend by slightly different amounts, spreading white light into its colors. The observer sees a circular arc with red on the outside and violet on the inside. Rainbows appear opposite the sun, which is why they show up when the sun is behind you."),
    ("Give me a short overview of the Renaissance.",
     "The Renaissance was a period of cultural revival in Europe roughly from the fourteenth to the seventeenth century. It began in the Italian city-states and drew inspiration from classical Greek and Roman ideas. Art flourished with figures like Leonardo and Michelangelo, emphasizing realism and perspective. Advances also came in science, literature, and exploration. The movement gradually reshaped how Europeans viewed knowledge and the individual."),
    ("How do bees make honey?",
     "Bees collect nectar from flowers using their long tongues and store it in a special stomach. Back at the hive they pass it between workers, adding enzymes that break down the sugars. They deposit the processed nectar into wax comb cells. By fanning their wings they evaporate moisture until it thickens into honey. Finally they cap the cell with wax to preserve it as food for the colony."),
    ("What is the significance of the Great Barrier Reef?",
     "The Great Barrier Reef off northeastern Australia is the world's largest coral reef system, stretching over two thousand kilometers. It is made up of thousands of individual reefs and hundreds of islands built by tiny coral polyps. The reef supports an enormous diversity of marine life, from fish and turtles to sharks and mollusks. It is visible from space and is a major natural wonder. Warming seas and bleaching events are ongoing threats to its health."),
    ("Explain how mountains are formed.",
     "Most large mountain ranges form where tectonic plates collide over millions of years. When two plates push together, the crust crumples and thrusts upward into folds. Some mountains rise where one plate dives beneath another and magma feeds volcanoes. Others form when blocks of crust are lifted along faults. Erosion by wind, water, and ice then sculpts the peaks over time."),
    ("Tell me about the invention of the printing press.",
     "Johannes Gutenberg introduced movable-type printing to Europe around the middle of the fifteenth century. His system used individual metal letters that could be arranged, inked, and pressed onto paper, then rearranged for the next page. This made books far faster and cheaper to produce than hand copying. The result was a rapid spread of literacy and ideas across the continent. It is often credited as a turning point toward the modern era."),
    ("How does human hearing work?",
     "Sound waves enter the outer ear and travel down the canal to the eardrum, making it vibrate. Three tiny bones in the middle ear amplify those vibrations. They pass into the fluid-filled cochlea, where thousands of hair cells convert motion into nerve signals. The auditory nerve carries those signals to the brain. The brain interprets them as pitch, volume, and meaning."),
    ("What are the main phases of the Moon?",
     "The Moon cycles through phases as its position relative to the Earth and Sun changes. It begins at the new moon, invisible because its lit side faces away from us. It waxes through crescent, first quarter, and gibbous to the full moon, fully illuminated. Then it wanes back through gibbous, last quarter, and crescent. The full cycle takes about twenty-nine and a half days."),
    ("Give a brief history of the Olympic Games.",
     "The ancient Olympic Games began in Olympia, Greece, nearly three thousand years ago as a religious and athletic festival. They were held every four years and drew competitors from across the Greek world. The events included running, wrestling, and chariot racing. The modern Olympics were revived in the late nineteenth century by Pierre de Coubertin. They have since grown into a global event held in cities around the world."),
    ("How do plants adapt to deserts?",
     "Desert plants survive scarce water through a range of adaptations. Many have deep or wide root systems to capture whatever moisture is available. Some, like cacti, store water in thick stems and reduce leaves to spines to limit evaporation. Waxy coatings and the ability to open pores mainly at night further conserve water. Some seeds simply wait dormant until rare rains arrive."),
    ("What is the story behind the Eiffel Tower?",
     "The Eiffel Tower was built as the centerpiece of the 1889 World's Fair in Paris, marking a century since the French Revolution. Designed by Gustave Eiffel's engineering firm, it was the tallest man-made structure at the time. Many critics initially considered it an eyesore. It was nearly dismantled but was saved partly by its usefulness for radio transmission. Today it is one of the most recognized landmarks in the world."),
    ("Explain how volcanoes erupt.",
     "Volcanoes erupt when molten rock, called magma, rises toward the surface. Deep underground, heat and pressure keep rock partially melted and buoyant. Dissolved gases in the magma expand as it ascends, driving it upward. When it breaks through a vent, it emerges as lava, ash, and gas. The style of eruption depends on how thick and gas-rich the magma is."),
    ("Tell me about the migration of monarch butterflies.",
     "Monarch butterflies undertake one of the longest insect migrations known. Each autumn, monarchs in North America travel thousands of kilometers to overwintering sites, many reaching central Mexico. Remarkably, no single butterfly makes the whole round trip; it spans several generations. They navigate using the sun and an internal sense of time. In spring their descendants head north again to breed."),
    ("What is the purpose of the Great Wall of China?",
     "The Great Wall of China was built over many centuries by different dynasties, mainly for defense. It served to slow and channel invasions from northern nomadic groups. Beyond a barrier, it functioned as a network of watchtowers and signal stations for early warning. It also helped regulate trade and movement along its length. Stretching thousands of kilometers, it is one of the largest construction projects in history."),
    ("How does a compass work?",
     "A compass works because the Earth behaves like a giant magnet with poles near its geographic north and south. The compass needle is a small magnet free to rotate. It aligns itself with the Earth's magnetic field, pointing roughly toward magnetic north. Navigators use that reference to determine direction. Nearby metal or magnets can disturb the reading, so it must be used with care."),
    ("Describe the life cycle of a star like the Sun.",
     "A star like the Sun begins as a collapsing cloud of gas and dust that heats until fusion ignites. For most of its life it steadily fuses hydrogen into helium, a stable phase lasting billions of years. As hydrogen runs low it swells into a red giant. It then sheds its outer layers, leaving a glowing shell around a dense core. That core cools slowly as a white dwarf over immense timescales."),
    ("What is the significance of the Nile to ancient Egypt?",
     "The Nile was the lifeline of ancient Egyptian civilization. Its yearly flooding deposited rich silt that made farming possible in an otherwise arid land. Egyptians timed planting and harvest around the flood cycle. The river was also the main highway for transport and trade. Its reliability supported the stable, long-lasting society that built the pyramids."),
    ("How do submarines dive and surface?",
     "Submarines control depth using ballast tanks. To dive, they flood the tanks with seawater, increasing weight so the vessel sinks. To surface, they force the water out with compressed air, making the submarine buoyant again. Fine adjustments come from small control surfaces and trim tanks. This balance of weight and buoyancy lets a submarine hold a chosen depth."),
    ("Give me an overview of the human circulatory system.",
     "The circulatory system moves blood, nutrients, and oxygen throughout the body. The heart acts as a pump with four chambers. Arteries carry oxygen-rich blood away from the heart to the tissues. Veins return oxygen-poor blood back to be reoxygenated in the lungs. Tiny capillaries connect the two and allow exchange with cells."),
    ("What causes the seasons on Earth?",
     "Seasons are caused by the tilt of the Earth's axis, not its distance from the Sun. As the planet orbits, different hemispheres lean toward or away from the Sun. The hemisphere tilted toward the Sun receives more direct light and longer days, producing summer. The opposite hemisphere experiences winter at the same time. The tilt stays roughly constant, so the pattern repeats each year."),
    ("Tell me about the discovery of penicillin.",
     "Penicillin was discovered by Alexander Fleming in 1928, largely by accident. He noticed that a mold contaminating a bacterial culture had killed the bacteria around it. The mold produced a substance that inhibited bacterial growth. Later researchers developed methods to purify and mass-produce it. It became one of the first widely used antibiotics and transformed medicine."),
    ("How do glaciers shape the landscape?",
     "Glaciers are slow-moving masses of ice that reshape land as they flow. Their weight and movement grind and pluck rock from the ground beneath them. They carve wide U-shaped valleys and sharp ridges over long periods. As they melt and retreat they leave behind deposits of rock and debris. Many lakes and fjords are remnants of past glacial activity."),
    ("What is the role of the honeybee in pollination?",
     "Honeybees are important pollinators for many flowering plants and crops. As they gather nectar, pollen sticks to their bodies. Moving from flower to flower, they transfer that pollen and enable plants to produce seeds and fruit. This service supports both wild ecosystems and agriculture. A decline in bee populations can therefore affect food supplies."),
    ("Explain how a bridge supports weight.",
     "Bridges carry weight by directing forces into supports and foundations. In a beam bridge, the deck bends slightly and passes loads to piers at each end. Arch bridges channel weight outward along a curve into the ground. Suspension bridges hang the deck from cables draped over tall towers. Each design manages tension and compression so the structure stays stable."),
    ("What was the Silk Road?",
     "The Silk Road was a network of trade routes connecting East Asia with the Middle East and Europe. It carried not only silk but spices, precious metals, and many other goods. Just as importantly, it spread ideas, religions, and technologies between distant cultures. Caravans crossed deserts and mountains, stopping at trading cities along the way. It shaped commerce and exchange for many centuries."),
    ("How do birds fly?",
     "Birds fly by generating lift and thrust with their wings. The curved shape of a wing makes air move faster over the top than the bottom, lowering pressure above and lifting the bird. By flapping, they push air backward and downward to move forward and stay aloft. Their light, hollow bones and strong chest muscles make this efficient. They steer and brake using their tail and wing angles."),
]

REMINDER = ("\n\n(Reminder: apply the engineering guidance established at the start "
            "of this session — review your code against it before finishing.)")


def guidance_text(case):
    ctx = "\n\n".join(open(os.path.join(ROOT, s), encoding="utf-8").read() for s in case["skills"])
    return (f"For everything you build in this session, apply the following "
            f"engineering guidance and do not present incomplete code:\n\n"
            f"{_rc.principle5()}\n\n{ctx}")


def chat(model, messages, k, max_tokens=32000, temp=0.0):
    body = json.dumps({"model": model, "messages": messages,
                       "temperature": temp, "max_tokens": max_tokens}).encode()
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                "https://openrouter.ai/api/v1/chat/completions", data=body,
                headers={"Authorization": f"Bearer {k}", "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            last = e
            import time
            time.sleep(3 * (attempt + 1))
    raise last


def build_messages(case, arm, depth):
    msgs = []
    if arm in ("anchor", "reminder"):
        msgs.append({"role": "user", "content": guidance_text(case)})
        msgs.append({"role": "assistant",
                     "content": "Understood. I'll apply that engineering guidance to everything I build this session."})
    for u, a in FILLER[:depth]:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    probe = case["task"] + (REMINDER if arm == "reminder" else "")
    msgs.append({"role": "user", "content": probe})
    return msgs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="c6_webhook")
    ap.add_argument("--depths", default="0,12,30")
    ap.add_argument("--build-model", default="anthropic/claude-sonnet-4.6")
    ap.add_argument("--judge-model", default="anthropic/claude-opus-4.8")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    k = _rc.key()
    case = next(c for c in _rc.load_cases() if c["id"] == a.task)
    depths = [int(x) for x in a.depths.split(",")]
    arms = ["control", "anchor", "reminder"]
    print(f"task={a.task}  arms={arms}  depths={depths}  build={a.build_model}  "
          f"judge={a.judge_model}  (multi-turn decay, blind judge)\n")
    results = {}
    for arm in arms:
        results[arm] = {}
        for d in depths:
            msgs = build_messages(case, arm, d)
            turns = len(msgs)
            print(f"  {arm:9s} depth={d:>2d} ({turns} msgs) generating…", flush=True)
            art = chat(a.build_model, msgs, k)
            verdict = _rc.judge(art, case["rubric"], a.judge_model, k)
            present = [r["id"] for r in case["rubric"] if verdict.get(r["id"]) == "present"]
            recall = len(present) / len(case["rubric"])
            results[arm][d] = {"recall": recall, "present": present,
                               "missing": [r["id"] for r in case["rubric"] if r["id"] not in present],
                               "artifact_len": len(art), "msgs": turns}
            print(f"  {arm:9s} depth={d:>2d} recall={recall:.2f}  missing: {', '.join(results[arm][d]['missing']) or '-'}", flush=True)
            if a.out:
                json.dump({"task": a.task, "depths": depths, "results": results}, open(a.out, "w"), indent=1)
    print("\nrecall by arm × filler-depth (turns of unrelated context after the guidance):")
    hdr = "  ".join(f"K={d}" for d in depths)
    print(f"  {'arm':9s} {hdr}")
    for arm in arms:
        print(f"  {arm:9s} " + "  ".join(f"{results[arm][d]['recall']:.2f}" for d in depths))
    a0, aK = results["anchor"][depths[0]]["recall"], results["anchor"][depths[-1]]["recall"]
    rK = results["reminder"][depths[-1]]["recall"]
    print(f"\nDECAY (anchor K{depths[0]}→K{depths[-1]}): {a0:.2f} → {aK:.2f}  ({aK-a0:+.2f})")
    print(f"REMINDER RECOVERY at K{depths[-1]}: anchor {aK:.2f} → reminder {rK:.2f}  ({rK-aK:+.2f})")
    if a.out:
        print(f"saved {a.out}")


if __name__ == "__main__":
    main()
