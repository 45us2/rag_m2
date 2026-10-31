# Smoke test 2026-10-31 19:11 (gemini-3.5-flash-lite)

Routing: 13/13 as expected

## How does Lone Operative work?

*route: rules (expected rules) OK · query: How does Lone Operative work?*


Unless part of an Attached unit, a unit with the Lone Operative ability can only be selected as the target of a ranged attack if the attacking model is within 12" (Core Rules: Lone Operative).

*sources: rules: LONE OPERATIVE | MAKE RANGED ATTACKS; rules: INFILTRATORS; rules: AIRCRAFT | DEPLOYING AIRCRAFT*

---

## Can a unit charge after it Advanced?

*route: rules (expected rules) OK · query: Can a unit charge after it Advanced?*


No. A unit cannot declare a charge or charge in the same turn that it Advanced (Core Rules: Charge Bonus; Core Rules: Advance Moves).

*sources: rules: CHARGE PHASE | CHARGE BONUS; rules: DISEMBARK; rules: ADVANCE MOVES; rules: CHARGING WITH A UNIT; rules: HEROIC INTERVENTION*

---

## What happens when a unit fails a Battle-shock test?

*route: rules (expected rules) OK · query: What happens when a unit fails a Battle-shock test?*


When a unit fails a Battle-shock test, that unit is Battle-shocked until the start of your next Command phase (Core Rules: 2. BATTLE-SHOCK). 

While a unit is Battle-shocked:
* The Objective Control characteristic of all its models is 0.
* If it Falls Back, you must take a Desperate Escape test for every model in that unit.
* Its controlling player cannot use Stratagems to affect that unit (Core Rules: 2. BATTLE-SHOCK).

(Core Rules: 2. BATTLE-SHOCK)

*sources: rules: INSANE BRAVERY; rules: 2. BATTLE-SHOCK; rules: Desperate Escape Tests*

---

## How do invulnerable saves work against mortal wounds?

*route: rules (expected rules) OK · query: How do invulnerable saves work against mortal wounds?*


No saving throws (including invulnerable saving throws) can be made against mortal wounds (Core Rules: Mortal Wounds).

*sources: rules: MORTAL WOUNDS; rules: INVULNERABLE SAVES; rules: DEVASTATING WOUNDS; rules: Hints and Tips FAST DICE ROLLING*

---

## describe me Time to Strike

*route: sql (expected sql) OK · query: Time to Strike*

`Query: SELECT DISTINCT s.id, s.name, s.type, s.cpCost, s.phase, s.description, f.name AS faction_name FROM stratagems s LEFT JOIN factions f ON f.Id = s.FactionId WHERE s.name LIKE '%Time to Strike%' LIMIT 30`

**TIME TO STRIKE** (Guardian Battlehost – Strategic Ploy Stratagem)
* **CP Cost:** 1
* **Phase:** Movement phase
* **WHEN:** Your Movement phase.
* **TARGET:** One Storm Guardians unit from your army that has not been selected to move this phase.
* **EFFECT:** Until the end of the phase, each time your unit Advances, do not make an Advance roll. Instead, until the end of the phase, add 6" to the Move characteristic of models in your unit. Until the end of the turn, your unit is eligible to shoot and declare a charge in a turn in which it Advanced.

(Game database)

*sources: sql*

---

## Which Aeldari stratagems can be used in the Movement phase?

*route: sql (expected sql) OK · query: Which Aeldari stratagems can be used in the Movement phase?*

`Query: SELECT DISTINCT s.name AS stratagem_name, s.cpCost, s.phase, s.description, f.name AS faction_name FROM stratagems s JOIN factions f ON s.FactionId = f.Id WHERE f.name LIKE '%Aeldari%' AND s.phase LIKE '%Movement%'`

The Aeldari stratagems that can be used in the Movement phase are:

* **STAR ENGINES** (Game database)
* **OPPORTUNITY SEIZED** (Game database)
* **SWIFT AS THE WIND** (Game database)
* **FLITTING SHADOWS** (Movement or Charge phase) (Game database)
* **VECTORED ENGINES** (Game database)
* **KHAINE’S VENGEANCE** (Game database)
* **LETHAL RUSE** (Game database)
* **DECEPTIVE FEINT** (Game database)
* **MOCKING FLIGHT** (Game database)
* **TRICKSTERS’ RETORT** (Game database)
* **TIME TO STRIKE** (Game database)
* **SHIELD OF BLADES** (Movement or Charge phase) (Game database)
* **RAPID AMBUSH** (Game database)
* **ISHA’S FURY** (Game database)
* **UNSHROUDED TRUTH** (Game database)
* **WEAVING STRIDE** (Game database)
* **SPIRIT TOKEN** (Game database)
* **ACROBATIC LEAPS** (Game database)
* **CAPTIVATING PERFORMANCE** (Game database)
* **FEIGNED RETREAT** (Game database)
* **DARING RIDERS** (Game database)
* **WIND OF BLADES** (Game database)
* **UNFLINCHING FIRE** (Movement or Charge phase) (Game database)

*sources: sql*

---

## What is the toughness and save of an Intercessor Squad?

*route: sql (expected sql) OK · query: What is the toughness and save of an Intercessor Squad?*

`Query: SELECT DISTINCT d.name AS datasheet_name, dm.name AS model_name, dm.t AS toughness, dm.sv AS save FROM datasheets d JOIN datasheets_models dm ON dm.DatasheetId = d.Id WHERE d.name LIKE '%Intercessor Squad%' LIMIT 30`

The toughness of an Intercessor Squad is 4, and its save is 3+ (Game database).

*sources: sql*

---

## How many points does a Land Raider cost?

*route: sql (expected sql) OK · query: How many points does a Land Raider cost?*

`Query: SELECT DISTINCT d.name AS datasheet_name, dmc.description, dmc.cost FROM datasheets d JOIN datasheets_models_cost dmc ON dmc.DatasheetId = d.Id WHERE d.name LIKE '%Land Raider%' LIMIT 30`

Based on the database, a Land Raider costs either 220 points or 240 points (depending on the unit quantity tier).

(Game database)

*sources: sql*

---

## Does Eldrad Ulthran have the Lone Operative ability, and what does it do?

*route: both (expected both) OK · query: Does Eldrad Ulthran have the Lone Operative ability, and what does it do?*

`Query: SELECT DISTINCT d.name AS datasheet_name, COALESCE(NULLIF(da.name, ''), a.name) AS ability_name, COALESCE(da.description, a.description) AS ability_description FROM datasheets d LEFT JOIN datasheets_abilities da ON da.DatasheetId = d.Id LEFT JOIN abilities a ON a.Id = da.abilityId WHERE d.name LIKE '%Eldrad%' AND (da.name LIKE '%Lone Operative%' OR a.name LIKE '%Lone Operative%' OR COALESCE(da.description, a.description) LIKE '%Lone Operative%') LIMIT 30`

Based on the provided database, Eldrad Ulthran does not have the Lone Operative ability listed in his abilities (Game database). 

However, the **Lone Operative** rule in the Core Rules states:
* Unless part of an Attached unit, a unit with this ability can only be selected as the target of a ranged attack if the attacking model is within 12" (Core Rules: Lone Operative | Make Ranged Attacks).

(Core Rules: Lone Operative | Make Ranged Attacks; Game database)

*sources: rules: LONE OPERATIVE | MAKE RANGED ATTACKS; rules: PSYCHIC WEAPONS AND ABILITIES | DEPLOYMENT ABILITIES; rules: FEEL NO PAIN; sql*

---

## What weapons does a Hellblaster Squad have?

*route: sql (expected sql) OK · query: What weapons does a Hellblaster Squad have?*

`Query: SELECT DISTINCT d.name AS datasheet_name, dw.name AS weapon_name, dw.range, dw.type, dw.a, dw.bsWs, dw.s, dw.ap, dw.d, dw.description FROM datasheets d JOIN datasheets_wargear dw ON dw.DatasheetId = d.Id WHERE d.name LIKE '%Hellblaster Squad%' LIMIT 30`

A Hellblaster Squad has the following weapons:
* Bolt pistol (Range: 12", Type: Ranged, A: 1, BS/WS: 3, S: 4, AP: 0, D: 1, Description: pistol)
* Close combat weapon (Range: Melee, Type: Melee, A: 3, BS/WS: 3, S: 4, AP: 0, D: 1)
* Plasma incinerator – standard (Range: 24", Type: Ranged, A: 2, BS/WS: 3, S: 7, AP: -2, D: 1, Description: assault, heavy)
* Plasma incinerator – supercharge (Range: 24", Type: Ranged, A: 2, BS/WS: 3, S: 8, AP: -3, D: 2, Description: assault, hazardous, heavy)
* Plasma pistol – standard (Range: 12", Type: Ranged, A: 1, BS/WS: 3, S: 7, AP: -2, D: 1, Description: pistol)
* Plasma pistol – supercharge (Range: 12", Type: Ranged, A: 1, BS/WS: 3, S: 8, AP: -3, D: 2, Description: hazardous, pistol)

(Game database)

*sources: sql*

## and what is their toughness?

*route: sql (expected sql) OK · query: what is the toughness of a Hellblaster Squad?*

`Query: SELECT DISTINCT d.name AS datasheet_name, dm.name AS model_name, dm.t AS toughness FROM datasheets d JOIN datasheets_models dm ON dm.DatasheetId = d.Id WHERE d.name LIKE '%Hellblaster Squad%' LIMIT 30`

The toughness of a Hellblaster Squad is 4 (Game database).

*sources: sql*

## can they shoot after Falling Back?

*route: both (expected rules|both) OK · query: can a Hellblaster Squad shoot after Falling Back*

`Query: SELECT DISTINCT d.name AS datasheet_name, s.name AS stratagem_name, s.description AS stratagem_description FROM datasheets d LEFT JOIN datasheets_stratagems ds ON ds.DatasheetId = d.Id LEFT JOIN stratagems s ON s.id = ds.stratagemId WHERE d.name LIKE '%Hellblaster Squad%' AND (s.description LIKE '%Fall Back%' OR s.name LIKE '%Fall Back%') LIMIT 30`

Yes, a Hellblaster Squad can shoot after Falling Back if it uses the **Scions of Guilliman** stratagem. 

* **Scions of Guilliman**
  * **When:** Your Movement phase, just after an Adeptus Astartes unit from your army ends a Fall Back move.
  * **Target:** That Adeptus Astartes unit.
  * **Effect:** Until the end of the turn, your unit is eligible to shoot and declare a charge in a turn in which it Fell Back.

(Game database)

*sources: rules: Desperate Escape Tests; rules: FALL BACK MOVES; rules: FIRE OVERWATCH; rules: EMBARK; sql*

---

## hello!

*route: none (expected none) OK · query: hello!*


Hello! How can I help you with Warhammer 40,000 rules today?

*sources: -*

---
