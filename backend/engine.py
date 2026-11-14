"""Deterministic, source-linked demo extraction. No ground-truth candidate lookup."""
from collections import defaultdict, deque
from copy import deepcopy
import hashlib
import json
import re
from .dna import check, fitting_relationships, relationship
from .models import Citation, Claim, validate_citation


def stable_id(prefix, value):
    return prefix + hashlib.sha256(value.encode("utf8")).hexdigest()[:14]


def unique_citations(items):
    unique = {(c["document_id"], c["start_line"], c["end_line"], c["quote"]): c for c in items}
    return [unique[key] for key in sorted(unique)]


def extract(state):
    people = {p["id"]: {**p, "birth_year": None, "death_year": None, "locations": []} for p in state["roster"]}
    names = {p["name"].casefold(): p["id"] for p in people.values()}
    claims = []

    def person(name):
        name = name.strip()
        key = name.casefold()
        if key not in names:
            pid = stable_id("p-", key)
            names[key] = pid
            people[pid] = {"id": pid, "name": name, "birth_year": None, "death_year": None, "locations": [], "candidate": False}
        return names[key]

    for document in sorted(state["documents"], key=lambda d: d["id"]):
        if not document["processed"]:
            continue
        for line_number, raw in enumerate(document["text"].split("\n"), 1):
            line = raw.strip()
            if not line:
                continue
            citation = Citation(document_id=document["id"], quote=line, start_line=line_number, end_line=line_number)

            def add(kind, subject, value=None, object_id=None, location=None):
                claim = Claim(kind=kind, subject=subject, value=value, object_id=object_id, location=location, citation=citation)
                if validate_citation(citation, state["documents"]):
                    claims.append(claim.model_dump())

            match = re.fullmatch(r"Candidate lead: (.{2,100})\.", line)
            if match:
                people[person(match[1])]["candidate"] = True
                continue
            match = re.fullmatch(r"(.{2,100}?) was born in (\d{4})(?: in (.{2,150}?))?\.", line)
            if match:
                add("birth", person(match[1]), int(match[2]), location=match[3]); continue
            match = re.fullmatch(r"(.{2,100}?) died in (\d{4})\.", line)
            if match:
                add("death", person(match[1]), int(match[2])); continue
            match = re.fullmatch(r"(.{2,100}?) was recorded alive in (\d{4})(?: in (.{2,150}?))?\.", line)
            if match:
                add("alive", person(match[1]), int(match[2]), location=match[3]); continue
            match = re.fullmatch(r"(.{2,100}?) is the (?:son|daughter|child) of (.{2,100}?) and (.{2,100}?)\.", line)
            if match:
                child = person(match[1])
                add("parent", person(match[2]), object_id=child)
                add("parent", person(match[3]), object_id=child); continue
            match = re.fullmatch(r"(.{2,100}?) is a parent of (.{2,100}?)\.", line)
            if match:
                add("parent", person(match[1]), object_id=person(match[2])); continue
            match = re.fullmatch(r"(.{2,100}?) married (.{2,100}?)\.", line)
            if match:
                add("spouse", person(match[1]), object_id=person(match[2])); continue
            match = re.fullmatch(r"Estimated birth year range: (\d{4})-(\d{4})\.", line)
            if match and int(match[1]) <= int(match[2]):
                add("birth_range", "case", f"{match[1]}:{match[2]}"); continue
            match = re.fullmatch(r"Estimated death year: (\d{4})\.", line)
            if match:
                add("case_death", "case", int(match[1])); continue
            match = re.fullmatch(r"Case region: (.{2,100})\.", line)
            if match:
                add("case_region", "case", match[1]); continue
            match = re.fullmatch(r"DNA match: Unidentified individual and (.{2,100}?) share (\d{1,4}) cM \(simulated\)\.", line)
            if match and 0 < int(match[2]) <= 4000:
                add("dna_match", "case", int(match[2]), object_id=person(match[1]))
    # Source-verified AI extraction (backend/extraction.py). Only claims that passed verification are used,
    # and each citation is re-checked against the current document text.
    processed = {d["id"] for d in state["documents"] if d["processed"]}
    for document_id, result in sorted(state.get("ai_extractions", {}).items()):
        if document_id not in processed:
            continue
        for item in result.get("accepted", []):
            citation = Citation.model_validate(item["citation"])
            if not validate_citation(citation, state["documents"]):
                continue
            subject = person(item["person"])
            other = person(item["other_person"]) if item.get("other_person") else None
            if item["kind"] in ("parent", "spouse", "sibling"):
                if other is None or other == subject:
                    continue
                claim = Claim(kind=item["kind"], subject=subject, object_id=other, citation=citation)
            else:
                claim = Claim(kind=item["kind"], subject=subject, value=item.get("year"), location=item.get("place"), citation=citation)
            claims.append(claim.model_dump())
    return people, claims


def derive(state):
    people, claims = extract(state)
    by_person = defaultdict(list)
    for claim in claims:
        by_person[claim["subject"]].append(claim)
        if claim["subject"] in people and claim["location"]:
            people[claim["subject"]]["locations"].append(claim["location"])
    for pid, p in people.items():
        for kind, field in [("birth", "birth_year"), ("death", "death_year")]:
            values = [c["value"] for c in by_person[pid] if c["kind"] == kind]
            p[field] = values[0] if values else None  # Display only; constraints use ALL claims below.
        p["locations"] = sorted(set(p["locations"]))

    relationships_map = {}
    for c in claims:
        if c["kind"] not in ("parent", "spouse", "sibling"):
            continue
        source, target = c["subject"], c["object_id"]
        if c["kind"] in ("spouse", "sibling"):
            source, target = sorted([source, target])
        key = f"{c['kind']}:{source}:{target}"
        r = relationships_map.setdefault(key, {"id": stable_id("r-", key), "source": source, "target": target, "type": c["kind"], "status": "supported", "citations": []})
        r["citations"].append(c["citation"])
    relationships = sorted(relationships_map.values(), key=lambda r: r["id"])
    for r in relationships:
        r["citations"] = unique_citations(r["citations"])
    findings = []

    def finding(kind, title, description, person_ids, citations, key=None):
        findings.append({"id": stable_id("f-", key or kind + title), "kind": kind, "title": title, "description": description,
                         "severity": "warning" if kind in ("conflict", "exclusion", "ai_rejected") else "info", "person_ids": person_ids, "citations": unique_citations(citations)})

    for r in relationships:
        source, target = people[r["source"]]["name"], people[r["target"]]["name"]
        finding("relationship", f"{source} → {target}", f"The source asserts a {r['type']} relationship. Source-backed does not mean independently certified.", [r["source"], r["target"]], r["citations"], r["id"])
    conflicts = set()
    for pid in people:
        for kind in ("birth", "death"):
            records = [c for c in by_person[pid] if c["kind"] == kind]
            years = sorted(set(c["value"] for c in records))
            if len(years) > 1:
                conflicts.add(pid)
                finding("conflict", f"{people[pid]['name']}: conflicting {kind} years", f"Sources report {', '.join(map(str, years))}. All assertions are retained; the first source year is used only for the graph label. Resolve the discrepancy before relying on it.", [pid], [c["citation"] for c in records])
        deaths = [c for c in by_person[pid] if c["kind"] == "death"]
        alive = [c for c in by_person[pid] if c["kind"] == "alive"]
        if deaths and any(a["value"] > min(d["value"] for d in deaths) for a in alive):
            conflicts.add(pid)
            finding("conflict", f"{people[pid]['name']}: life-status conflict", "An alive record postdates a death assertion. Verify source accuracy and whether the records describe the same person.", [pid], [c["citation"] for c in deaths + alive])

    for child in people:
        asserted = [r for r in relationships if r["type"] == "parent" and r["target"] == child]
        if len({r["source"] for r in asserted}) > 2:
            conflicts.add(child)
            for r in asserted:
                r["status"] = "disputed"
            finding("conflict", f"{people[child]['name']}: multiple parent assertions", "Sources name more than two parents. This may reflect adoption, a blended family, name linkage or a source error; do not collapse these assertions into one biological pedigree.", [child], [c for r in asserted for c in r["citations"]])
        for relation in asserted:
            parent = relation["source"]
            parent_births = [c for c in by_person[parent] if c["kind"] == "birth"]
            child_births = [c for c in by_person[child] if c["kind"] == "birth"]
            if parent == child or (parent_births and child_births and min(c["value"] for c in parent_births) >= max(c["value"] for c in child_births)):
                conflicts.add(child)
                relation["status"] = "disputed"
                finding("conflict", f"{people[child]['name']}: parent chronology needs review", "The asserted parent is the same person or the reported years place the parent no earlier than the child. Preserve the sources and verify linkage before treating this as a pedigree.", [parent, child], relation["citations"] + [c["citation"] for c in parent_births + child_births], "chronology-" + relation["id"])

    # Kahn's algorithm detects directed parent cycles without recursive traversal.
    indegrees = {pid: 0 for pid in people}
    children = defaultdict(list)
    for relation in relationships:
        if relation["type"] == "parent":
            indegrees[relation["target"]] += 1
            children[relation["source"]].append(relation["target"])
    queue = deque(pid for pid, count in indegrees.items() if count == 0)
    while queue:
        parent = queue.popleft()
        for child in children[parent]:
            indegrees[child] -= 1
            if indegrees[child] == 0:
                queue.append(child)
    affected = {pid for pid, count in indegrees.items() if count > 0}
    if affected:
        conflicts.update(affected)
        disputed = [r for r in relationships if r["type"] == "parent" and r["source"] in affected and r["target"] in affected]
        for relation in disputed:
            relation["status"] = "disputed"
        finding("conflict", "Parent graph contains a directed cycle", "Some parent assertions form a cycle. The assertions and dependent paths require human review and are excluded from family-path scoring; they do not establish a biological pedigree.", sorted(affected), [c for r in disputed for c in r["citations"]])

    # Conflicting constraints never silently select one source or drive an exclusion.
    constraints = {}
    for kind in ("birth_range", "case_death", "case_region"):
        observations = [c for c in claims if c["kind"] == kind]
        values = {str(c["value"]) for c in observations}
        if len(values) == 1:
            constraints[kind] = observations
        elif len(values) > 1:
            finding("conflict", f"Conflicting case constraint: {kind.replace('_', ' ')}", "Records disagree about a case constraint. The engine abstains from applying this constraint until it is reconciled.", [], [c["citation"] for c in observations])
    dna = [c for c in claims if c["kind"] == "dna_match"]
    for c in dna:
        finding("observation", f"Simulated DNA match: {c['value']} cM with {people[c['object_id']]['name']}", "Simulated shared-cM summary only. Multiple genealogical paths are possible; no relationship probability or sequence-level inference is claimed.", [c["object_id"]], [c["citation"]])

    # Recorded parent links, plus parents shared through recorded sibling links.
    parents, parent_links = defaultdict(set), {}
    for r in relationships:
        if r["type"] == "parent" and r["status"] == "supported":
            parents[r["target"]].add(r["source"])
            parent_links[(r["source"], r["target"])] = r["citations"]
    siblings = [r for r in relationships if r["type"] == "sibling" and r["status"] == "supported"]
    changed = True
    while changed:
        changed = False
        for r in siblings:
            for x, y in ((r["source"], r["target"]), (r["target"], r["source"])):
                for parent in sorted(parents[x] - parents[y]):
                    parents[y].add(parent); changed = True
                    parent_links[(parent, y)] = parent_links.get((parent, x), []) + r["citations"]
    for r in siblings:  # Siblings with no recorded parents are assumed to share an unrecorded parent couple.
        a, b = r["source"], r["target"]
        if not parents[a] and not parents[b]:
            for side in ("1", "2"):
                virtual = f"unrecorded-parent-{side}:{a}:{b}"
                parents[a].add(virtual); parents[b].add(virtual)
                parent_links[(virtual, a)] = parent_links[(virtual, b)] = r["citations"]
    match_ids = {c["object_id"] for c in dna}

    def dna_assessment(pid):
        output = []
        for c in dna:
            related = relationship(pid, c["object_id"], parents)
            result = {**check(c["value"], related), "match_person_id": c["object_id"]}
            cites = [c["citation"]] + ([x for link in related["links"] for x in parent_links.get(link, [])] if related else [])
            output.append((result, cites))
        return output

    # Propose further leads: born inside the estimated range and linked by recorded parents to a DNA match.
    proposed = set()
    if dna and "birth_range" in constraints:
        low, high = map(int, constraints["birth_range"][0]["value"].split(":"))
        for pid, p in people.items():
            years = {c["value"] for c in by_person[pid] if c["kind"] == "birth"}
            if p["candidate"] or pid in match_ids or not years or not all(low <= y <= high for y in years):
                continue
            if any(relationship(pid, m, parents) for m in match_ids):
                p["candidate"] = True; proposed.add(pid)

    candidates = []
    for pid, p in people.items():
        if not p["candidate"]:
            continue
        reasons, citations, score, excluded = [], [], 0, False
        births = [c for c in by_person[pid] if c["kind"] == "birth"]
        alive = [c for c in by_person[pid] if c["kind"] == "alive"]
        if births and "birth_range" in constraints:
            low, high = map(int, constraints["birth_range"][0]["value"].split(":"))
            years = sorted(set(c["value"] for c in births))
            matches = [low <= y <= high for y in years]
            citations += [c["citation"] for c in births + constraints["birth_range"]]
            if all(matches):
                score += 2; reasons.append(f"Reported birth year(s) {', '.join(map(str, years))} fit the estimated {low}–{high} range (+2). This is a provisional age constraint.")
            elif not any(matches):
                excluded = True; reasons.append(f"Excluded under the current age assumption: reported birth year(s) {', '.join(map(str, years))} fall outside {low}–{high}. Revisit if the estimated age changes.")
            else:
                conflicts.add(pid); reasons.append("Birth assertions disagree about eligibility; age filtering abstains for this lead.")
        else:
            reasons.append("Birth-range eligibility has not yet been established from reviewed evidence.")
        if "case_death" in constraints:
            year = constraints["case_death"][0]["value"]
            later = [c for c in alive if c["value"] > year]
            if later:
                excluded = True
                reasons.append(f"Excluded under the current same-person/source assumption: an alive record in {max(c['value'] for c in later)} postdates the case death estimate of {year}. Verify the attestation and person linkage.")
                citations += [c["citation"] for c in later + constraints["case_death"]]
            elif alive:
                score += 1; reasons.append("A pre-recovery life-status record exists (+1); it does not establish identity.")
                citations += [c["citation"] for c in alive]
        if "case_region" in constraints:
            region = constraints["case_region"][0]["value"]
            regional = [c for c in by_person[pid] if c["location"] and region.casefold() in c["location"].casefold()]
            if regional:
                score += 1; reasons.append(f"A source associates this lead with {region} (+1); regional overlap is weak evidence.")
                citations += [c["citation"] for c in regional + constraints["case_region"]]
        if pid in proposed:
            reasons.insert(0, "Proposed by Kinfold: born inside the estimated range and linked by recorded parents to the DNA match. Not named as a lead in any record.")
        dna_checks, dna_excluded = [], False
        for result, cites in dna_assessment(pid):
            match_name = people[result["match_person_id"]]["name"]
            dna_checks.append(result)
            citations += cites
            if result["status"] == "consistent":
                score += 3
                reasons.append(f"DNA fits (+3): recorded parent links make {p['name']} and {match_name} {result['relationship_label']} (reference {result['expected_low_cm']:,}–{result['expected_high_cm']:,} cM). The observed {result['observed_cm']:,} cM is inside that range. Consistency, not proof.")
            elif result["status"] == "inconsistent":
                excluded = dna_excluded = True
                reasons.append(f"Excluded by DNA under the recorded pedigree: {p['name']} and {match_name} would be {result['relationship_label']}, expected about {result['expected_low_cm']:,}–{result['expected_high_cm']:,} cM, but they share {result['observed_cm']:,} cM. This lead fits only if a recorded parent link is wrong (adoption, misattributed parentage or record linkage).")
            elif result["reason"] == "no_recorded_common_ancestor":
                reasons.append(f"DNA not checked: no recorded common ancestor links {p['name']} to {match_name} yet.")
            else:
                reasons.append(f"DNA not checked: no reference range for {result['relationship_label']}.")
        if pid in conflicts:
            reasons.append("Contradictory source assertions remain open for human review.")
        status = "excluded" if excluded else "needs_review" if pid in conflicts or not births else "possible"
        candidate = {"person_id": pid, "rank": 0, "status": status, "score": score, "reasons": reasons, "citations": unique_citations(citations),
                     "dna_checks": dna_checks, "proposed_by_engine": pid in proposed}
        candidates.append(candidate)
        if excluded:
            title = f"{p['name']}: DNA does not fit the recorded pedigree" if dna_excluded else f"{p['name']}: outside current constraints"
            finding("exclusion", title, " ".join(r for r in reasons if r.startswith("Excluded")), [pid], citations)
    candidates.sort(key=lambda c: (c["status"] == "excluded", -c["score"], people[c["person_id"]]["name"]))
    for rank, c in enumerate(candidates, 1):
        c["rank"] = rank
    actions = []
    dna_conflicts = [c for c in candidates if any(d["status"] == "inconsistent" for d in c["dna_checks"])]
    dna_fits = [c for c in candidates if c["status"] != "excluded" and any(d["status"] == "consistent" for d in c["dna_checks"])]
    if dna and dna_conflicts and not dna_fits:
        match = dna[0]
        match_name = people[match["object_id"]]["name"]
        fits = fitting_relationships(match["value"])
        labels = sorted({d["relationship_label"] for c in dna_conflicts for d in c["dna_checks"] if d["status"] == "inconsistent"})
        elders = [people[x]["name"] for x in sorted(parents.get(match["object_id"], ())) if x in people]
        where = f"the parents and siblings of {' and '.join(elders)}" if elders else f"{match_name}'s grandparents' other descendants"
        finding("exclusion", f"DNA does not fit any recorded lead", f"{match['value']:,} cM with {match_name} is too little for {', '.join(labels)}. It fits {', '.join(fits[:4])}.", [c["person_id"] for c in dna_conflicts], [match["citation"]], "dna-no-fit")
        actions.append({"id": "dna-branch-search", "title": f"Search branches that fit {match['value']:,} cM",
                        "reason": f"The amount fits {', '.join(fits[:4])}: relatives who share {match_name}'s grandparents or great-grandparents, not {match_name}'s nieces or nephews. Pull records on {where} and their descendants.",
                        "person_ids": [x for x in sorted(parents.get(match["object_id"], ())) if x in people], "document_ids": [match["citation"]["document_id"]]})
    pending = [d for d in state["documents"] if not d["processed"]]
    if pending:
        actions.append({"id": "review-pending", "title": f"Review {len(pending)} unprocessed records", "reason": "Run the investigation to extract supported patterns and evaluate the remaining evidence.", "person_ids": [], "document_ids": [d["id"] for d in pending[:2]]})
    for f in findings:
        if f["kind"] == "conflict":
            actions.append({"id": "action-" + f["id"], "title": "Resolve: " + f["title"], "reason": "Compare the cited originals and seek an independent public or synthetic corroborating record.", "person_ids": f["person_ids"], "document_ids": sorted({c["document_id"] for c in f["citations"]})})
    remaining = [c for c in candidates if c["status"] != "excluded"]
    if not pending and remaining:
        c = remaining[0]
        actions.append({"id": "independent-life-status", "title": "Seek independent life-status evidence", "reason": f"{people[c['person_id']]['name']} remains a research lead, not an identification. Verify source linkage before narrowing further.", "person_ids": [c["person_id"]], "document_ids": []})
    elif not pending and candidates:
        actions.append({"id": "revisit-constraints", "title": "Revisit assumptions and broaden the search", "reason": "All current leads are excluded under the reviewed constraints. Verify the case estimates and source linkage, then seek additional public or synthetic leads rather than forcing an identity.", "person_ids": [], "document_ids": sorted({c["citation"]["document_id"] for c in claims if c["subject"] == "case"})})
    if dna:
        actions.append({"id": "validate-dna-assumptions", "title": "Validate the DNA assumptions", "reason": "The match is simulated. An actual research workflow requires independent relationship evidence and validated genetic methods.", "person_ids": [dna[0]["object_id"]], "document_ids": [dna[0]["citation"]["document_id"]]})
    names_by_document = {d["id"]: d["name"] for d in state["documents"]}
    by_id = {d["id"]: d for d in state["documents"]}

    def line_citation(document_id, line_number=None):
        """Cite one real line of the record (the line the model pointed at, else the first non-empty line)."""
        lines = by_id[document_id]["text"].split("\n") if document_id in by_id else []
        if line_number and 1 <= line_number <= len(lines) and lines[line_number - 1].strip():
            return [{"document_id": document_id, "quote": lines[line_number - 1], "start_line": line_number, "end_line": line_number}]
        first = next(((n, line) for n, line in enumerate(lines, 1) if line.strip()), None)
        return [{"document_id": document_id, "quote": first[1], "start_line": first[0], "end_line": first[0]}] if first else []

    for document_id, result in sorted(state.get("ai_extractions", {}).items()):
        if document_id not in names_by_document:
            continue
        name = names_by_document[document_id]
        if result["source"] == "failed":
            finding("observation", f"AI extraction did not run: {name}", result["note"], [], line_citation(document_id), "ai-failed-" + document_id)
            continue
        origin = "live call" if result["source"] == "live" else f"replay of a recorded response ({result['recorded_at']})"
        if result.get("fallback_note"):
            origin += f"; {result['fallback_note']}"
        finding("ai_extraction", f"AI read {name}: {len(result['accepted'])} claims verified, {len(result['rejected'])} rejected",
                f"Gemini ({result['model']}, {origin}) proposed {result['proposed']} claims. Kinfold accepted only claims whose quote is verbatim in the record and names every person and year it asserts.",
                [], [c["citation"] for c in result["accepted"]][:6], "ai-" + document_id)
        for item in result["rejected"]:
            who = item["person"] + (f" → {item['other_person']}" if item.get("other_person") else "")
            year = f" · {item['year']}" if item.get("year") else ""
            finding("ai_rejected", f"Rejected AI claim: {item['kind']} · {who}{year}",
                    f"Not used: {item['reason']}. The model quoted: “{item['quote'][:200]}”", [], line_citation(document_id, item.get("start_line")), "ai-rejected-" + document_id + json.dumps(item, sort_keys=True))
    # Uploaded prose outside the documented grammar stays visible and contributes no invented facts.
    cited_ids = {c["citation"]["document_id"] for c in claims}
    for d in state["documents"]:
        if d["processed"] and d["id"] not in cited_ids:
            first = next(((i, line.strip()) for i, line in enumerate(d["text"].split("\n"), 1) if line.strip()), None)
            if first:
                finding("observation", f"Reviewed without structured extraction: {d['name']}", "The deterministic demo parser found no supported claim patterns. The original record remains available for manual review or a configured live extraction adapter.", [], [{"document_id": d["id"], "quote": first[1], "start_line": first[0], "end_line": first[0]}])
    # What the AI actually said, sealed by hash (backend/extraction.py:raw_sha256). Part of the manifest.
    ai_recordings = [{"document_id": document_id, "model": result.get("model"), "recorded_at": result.get("recorded_at"), "raw_sha256": result.get("raw_sha256")}
                     for document_id, result in sorted(state.get("ai_extractions", {}).items())
                     if document_id in names_by_document and result.get("source") != "failed"]
    snapshot = {"case": deepcopy(state["case"]), "people": list(people.values()), "relationships": relationships, "ai_recordings": ai_recordings,
                "documents": deepcopy(state["documents"]), "findings": findings + deepcopy(state.get("model_findings", [])), "candidates": candidates,
                "next_actions": actions[:6], "audit": deepcopy(state["audit"]),
                "metrics": {"documents_processed": sum(d["processed"] for d in state["documents"]), "supported_relationships": sum(r["status"] == "supported" for r in relationships), "conflicts": sum(f["kind"] == "conflict" for f in findings), "remaining_candidates": len(remaining)}}
    return snapshot
