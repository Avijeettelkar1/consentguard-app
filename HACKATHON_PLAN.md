# Reject-All Radar — Team Battle Plan

> **{Tech: Europe} × Almedia — "The Summer Lock-In," Berlin (one-day sprint).**
> Read this first. It's the single source of truth for what we're building today.

---

## 1. What we're building (one line)

**An AI robot that busts whole industries of websites for illegally spying on you — live, on a scoreboard.**

---

## 2. What it actually does (plain terms, no jargon)

Every website in the EU has a **"Reject All"** cookie button. By law, when you click it, the site must stop letting ad-trackers (Google, Facebook, etc.) watch you. **Most sites cheat** — the trackers keep firing anyway. That's illegal (GDPR).

- **What we already have (our head start):** a scanner that opens *one* website, clicks "Reject All," and catches the trackers that fire anyway. It grades the site, estimates the fine, and writes a legal complaint.
- **What we build today:** instead of one site, you type in a whole **category** — like *"top German news sites"* — and an **AI agent goes and busts all of them at once**, live, showing a scoreboard of who's breaking the law.

**The analogy:** we're going from *"a metal detector you wave over one bag"* → *"a robot that walks the whole airport and flags every bad bag by itself."*

---

## 3. The moment we're building toward (this is how we win)

Everything serves this 30-second demo:

> Type **"top German news sites"** → hit **RAID** →
> the board floods with real, famous companies →
> grades cascade to red **F** →
> trackers stream in as they're caught →
> a counter spins up to **"€2.3M in fines discovered — in 84 seconds"** →
> click the worst offender → **a ready-to-send legal complaint to the Berlin regulator.**

We end on one killer line no single-site tool could ever say:
> **"One tracker is illegally firing on 8 of the 10 biggest German news sites. This isn't one bad site — it's an industry-wide pattern."**

That's not a demo. That's a headline. **Judges vote for teams that *found* something, not just built something.**

---

## 4. How it works (the flow)

```
You type an industry
        ↓
[TAVILY]  finds the real live websites in that category      ← the robot's "eyes"
        ↓
[OUR SCANNER]  opens each site, clicks Reject All,
               catches the trackers that fire anyway         ← what we already built
        ↓
[OPENAI]  reads each site's cookie policy and decides
          guilty vs innocent — out loud, explaining why      ← the robot's "brain / lawyer"
        ↓
[COGNEE]  remembers patterns across ALL sites
          ("this tracker is on 8 of 10 sites")               ← the robot's "memory"
        ↓
LIVE SCOREBOARD: graded companies, fine counter,
                 one-click legal complaint with proof
```

---

## 5. The 3 partners (and why — we're required to use them)

The hackathon **requires at least 1 partner tech** and gives **bonus points** for using them well. We use all three, each doing a real job:

| Partner | Plain-English job | Think of it as… |
|---------|-------------------|-----------------|
| **Tavily** | "Find me the actual websites in this category." | The robot's **eyes on the internet** |
| **OpenAI** | "Read this policy and tell me if they're lying — explain why." | The robot's **brain / the lawyer** |
| **Cognee** | Remembers what it saw across every site to spot patterns. | The robot's **memory** |

**⚠️ Important:** our scanner currently uses Claude (Anthropic), which is **NOT a partner** here. We swap that one piece to **OpenAI** so we tick the box *and* get the bonus points. Everything else we already built stays.

---

## 6. The 3 "wow" pieces (build these, in order)

1. **AI reasons out loud (build first).** Stream OpenAI's thinking live: *"Site declares Google Analytics… but I'm watching a Facebook Pixel fire after Reject All, and it's not in their policy → violation."* Watching the AI *catch the lie* is the magic.
2. **"Receipts" — proof for every accusation.** One click shows the tracker caught in the act + the exact missing policy line. Kills the "is it hallucinating?" question.
3. **The industry-wide finding.** Cognee's cross-site pattern → the headline we end on.

---

## 7. Who builds what (assign these at matchmaking)

| Role | Owns | First task |
|------|------|-----------|
| **P1 — AI/Brain** | OpenAI analysis path (swap out Claude) + stream its reasoning to the screen | Get OpenAI reading a policy and printing a guilty/innocent verdict |
| **P2 — Discovery** | Tavily "industry → list of sites" endpoint | Type "german news" → get back 8 real URLs |
| **P3 — Orchestration** | The `/raid` endpoint that scans the whole list + Cognee memory | Loop our scanner over the list, collect results |
| **P4 — Frontend/Wow** | The live Radar scoreboard, fine counter, receipts drill-down | Board that fills in live as results arrive (reuse our design system) |
| **P5 — Demo/Pitch** | Loom video, README, rehearsing the live pitch, pre-caching demo data | Pick the 2 hero industries; pre-scan + cache them |

*(Fewer than 5 people? Merge P3 into P1, P5 into P4.)*

---

## 8. Timeline (submit by 19:00 — ~8 hours)

| Time | What |
|------|------|
| 10:00–10:45 | Matchmaking. Lock scope. **New public repo** `reject-all-radar`, pull in our scanner as a boilerplate. Redeem OpenAI / Tavily / Cognee keys. |
| 10:45–13:00 | P1 OpenAI swap · P2 Tavily discovery · P3 `/raid` scan loop · P4 live board |
| 13:00–15:30 | Cognee memory + "most pervasive tracker" · stream OpenAI reasoning to UI · fine counter |
| 15:30–17:00 | Receipts drill-down (proof) + one-click complaint · polish the wow moments |
| 17:00–18:00 | **Freeze features.** Pre-cache the 2 demo industries so the live demo can't fail. README + docs. |
| 18:00–19:00 | Record 2-min Loom. **Submit repo + video before 19:00.** |
| 19:00–20:00 | Rehearse the 5-min pitch 3×. |

---

## 9. What we must submit (or we're disqualified)

- ✅ **2-minute Loom video** — explain the solution + a live walkthrough.
- ✅ **Public GitHub repo** — with a clear README (setup + install), and docs listing every API/tool used.
- ✅ **Use ≥1 partner tech** — we use 3 (OpenAI, Tavily, Cognee).
- ✅ **Built newly at the hackathon** — our old scanner counts as an allowed *boilerplate*; the agent layer is new today. **Frame it this way — don't present it as a finished pre-existing product.**
- ✅ **Submit by 19:00.** Team of max 5.

---

## 10. If we're running out of time (cut in this order)

1. Drop Cognee graph → show a simple static "worst offenders" list instead.
2. Drop live streaming → play pre-cached results.
3. Drop deployment → demo locally (totally fine).

**NEVER cut:** the live scoreboard flooding with real companies getting graded **F**. That's the entire wow. Everything else is optional.

---

## Track & prize

- **Track: Open Innovation** (build anything; 3 teams advance). Judged on **creativity, technical complexity, + partner-tech bonus.**
- **1st place:** 600€ cash + $2,500 OpenAI credits · **2nd:** $1,500 · **3rd:** $1,000.

**One-line pitch to remember:** *"One URL was a tool. This is an enforcement engine."*
