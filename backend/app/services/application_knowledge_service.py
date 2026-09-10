from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit


def _meaningful_tokens(text: str) -> set[str]:
    stop_words = {
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
        "has", "he", "in", "is", "it", "its", "of", "on", "that", "the",
        "to", "was", "were", "will", "with", "user", "story", "ac",
        "acceptance", "criteria", "should", "must", "can", "able", "when",
        "then", "given", "verify", "check", "test", "page", "button",
    }
    tokens = re.findall(r"[a-zA-Z0-9_-]{2,}", text.lower())
    return {t for t in tokens if t not in stop_words}


def _normalize_path(url: str) -> str:
    try:
        parsed = urlsplit(url)
        path = parsed.path.rstrip("/")
        return path if path else "/"
    except Exception:
        return url


def _extract_element_locator(elem: dict[str, Any]) -> str:
    """Return verified selector from crawl evidence. NEVER invent selectors."""
    if elem.get("locator"):
        return str(elem["locator"])
    if elem.get("selector"):
        return str(elem["selector"])
    if elem.get("test_id"):
        return f'[data-testid="{elem["test_id"]}"]'
    if elem.get("element_id"):
        return f'#{elem["element_id"]}'
    if elem.get("name") and elem.get("tag") in {"input", "select", "textarea"}:
        return f'{elem["tag"]}[name="{elem["name"]}"]'
    if elem.get("placeholder"):
        return f'[placeholder="{elem["placeholder"]}"]'
    if elem.get("aria_label"):
        return f'[aria-label="{elem["aria_label"]}"]'
    if elem.get("css_selector") and elem.get("locator_validated", True):
        return str(elem["css_selector"])
    if elem.get("visible_text") and len(str(elem["visible_text"])) < 40:
        clean_text = str(elem["visible_text"]).replace('"', '\\"')
        return f'text="{clean_text}"'
    if elem.get("role") and elem.get("name"):
        return f'role={elem["role"]}[name="{elem["name"]}"]'
    return ""


def extract_relevant_application_knowledge(
    user_stories: list[dict[str, Any]],
    acceptance_criteria: list[dict[str, Any]],
    crawl_knowledge: dict[str, Any] | None,
    max_elements_per_page: int = 15,
) -> dict[str, Any] | None:
    """
    Extract focused, deterministic application context from crawl knowledge.
    Uses path-aware graph traversal to ensure required prerequisite pages
    (e.g., Login -> Dashboard -> Target Page) are always included in order,
    even when requirement text only mentions deep target pages.
    """
    if not crawl_knowledge or not isinstance(crawl_knowledge, dict):
        return None

    # Collect requirement terms
    req_terms: set[str] = set()
    for us in user_stories:
        req_terms.update(_meaningful_tokens(us.get("text", "") or us.get("title", "") or ""))
    for ac in acceptance_criteria:
        req_terms.update(_meaningful_tokens(ac.get("text", "") or ac.get("title", "") or ""))

    app_map = crawl_knowledge.get("application_map") or {}
    all_pages: list[dict[str, Any]] = list(app_map.get("pages") or crawl_knowledge.get("pages") or [])
    all_elements: list[dict[str, Any]] = list(crawl_knowledge.get("discovered_elements") or [])
    relationships: list[dict[str, Any]] = list(
        crawl_knowledge.get("navigation_relationships")
        or app_map.get("relationships")
        or []
    )

    # Reconstruct pages from elements if pages list is empty
    if not all_pages and all_elements:
        seen_urls = set()
        for el in all_elements:
            p_url = el.get("page_url")
            if p_url and p_url not in seen_urls:
                seen_urls.add(p_url)
                all_pages.append({"url": p_url, "title": el.get("page_title") or "Discovered Page"})

    root_url = crawl_knowledge.get("application_url") or ""
    if not root_url and all_pages:
        root_url = all_pages[0].get("url") or ""

    root_norm = _normalize_path(root_url) if root_url else "/"

    # Ensure root page is in all_pages
    has_root = any(_normalize_path(p.get("url") or "") == root_norm for p in all_pages)
    if not has_root and root_url:
        all_pages.insert(0, {
            "url": root_url,
            "title": crawl_knowledge.get("page_title") or "Application Root",
        })

    # Index pages and elements by normalized path
    pages_by_norm: dict[str, dict[str, Any]] = {}
    for p in all_pages:
        norm = _normalize_path(p.get("url") or "")
        if norm not in pages_by_norm:
            pages_by_norm[norm] = p

    elems_by_norm: dict[str, list[dict[str, Any]]] = {}
    for el in all_elements:
        norm = _normalize_path(el.get("page_url") or root_url)
        elems_by_norm.setdefault(norm, []).append(el)

    # Build directed navigation graph
    nav_graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    reverse_graph: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for rel in relationships:
        f_norm = _normalize_path(rel.get("from") or rel.get("source") or "")
        t_norm = _normalize_path(rel.get("to") or rel.get("target") or "")
        if f_norm and t_norm:
            nav_graph.setdefault(f_norm, []).append((t_norm, rel))
            reverse_graph.setdefault(t_norm, []).append((f_norm, rel))

    # BFS from root to compute shortest navigation paths and reachability
    shortest_path_from_root: dict[str, list[str]] = {root_norm: [root_norm]}
    queue = [root_norm]
    while queue:
        curr = queue.pop(0)
        for neighbor, _ in nav_graph.get(curr, []):
            if neighbor not in shortest_path_from_root:
                shortest_path_from_root[neighbor] = shortest_path_from_root[curr] + [neighbor]
                queue.append(neighbor)

    # Score each page by relevance to requirements
    scored_pages = []
    for page in all_pages:
        p_url = page.get("url") or ""
        p_norm = _normalize_path(p_url)
        p_title = page.get("title") or ""
        page_tokens = _meaningful_tokens(p_url + " " + p_title)

        page_elems = elems_by_norm.get(p_norm, [])
        elem_tokens: set[str] = set()
        for el in page_elems:
            name = el.get("name") or el.get("accessible_name") or el.get("label") or ""
            placeholder = el.get("placeholder") or ""
            elem_tokens.update(_meaningful_tokens(name + " " + placeholder))

        overlap = (page_tokens | elem_tokens) & req_terms
        score = len(overlap)
        scored_pages.append((score, p_norm, page, page_elems))

    # Sort pages by score descending
    scored_pages.sort(key=lambda x: x[0], reverse=True)

    # Target pages with positive scores (or top candidate if none match)
    target_page_norms = [norm for score, norm, _, _ in scored_pages if score > 0]
    if not target_page_norms and scored_pages:
        target_page_norms = [scored_pages[0][1]]

    # Collect required pages preserving discovered navigation path from root
    required_page_norms: list[str] = []

    # 1. Root page is ALWAYS included
    if root_norm not in required_page_norms:
        required_page_norms.append(root_norm)

    # 2. For each target page, include all prerequisite pages along discovered path from root
    for t_norm in target_page_norms:
        if t_norm in shortest_path_from_root:
            path = shortest_path_from_root[t_norm]
            for node in path:
                if node not in required_page_norms:
                    required_page_norms.append(node)
        else:
            # Backwards traversal if not directly reached by forward BFS from root
            backwards_path = [t_norm]
            curr = t_norm
            visited = {curr}
            while curr in reverse_graph and reverse_graph[curr]:
                prev_node, _ = reverse_graph[curr][0]
                if prev_node in visited:
                    break
                visited.add(prev_node)
                backwards_path.insert(0, prev_node)
                curr = prev_node
                if curr == root_norm or curr in shortest_path_from_root:
                    if curr in shortest_path_from_root:
                        prefix = shortest_path_from_root[curr]
                        backwards_path = prefix[:-1] + backwards_path
                    break
            for node in backwards_path:
                if node not in required_page_norms:
                    required_page_norms.append(node)

    # Build extracted pages
    extracted_pages = []
    included_urls = set(required_page_norms)
    for norm in required_page_norms:
        page_meta = pages_by_norm.get(norm) or {"url": norm, "title": "Application Page"}
        p_url = page_meta.get("url") or norm
        p_title = page_meta.get("title") or ""
        page_elems = elems_by_norm.get(norm, [])

        # Compact verified elements
        compact_elements = []
        for el in page_elems[:max_elements_per_page]:
            role = el.get("role") or el.get("tag") or "element"
            name = el.get("name") or el.get("accessible_name") or el.get("label") or el.get("placeholder") or ""
            locator = _extract_element_locator(el)
            test_id = el.get("test_id") or el.get("data_testid") or ""
            item: dict[str, Any] = {
                "role": role,
                "name": name,
            }
            if locator:
                item["locator"] = locator
            if test_id:
                item["test_id"] = test_id
            if el.get("placeholder"):
                item["placeholder"] = el.get("placeholder")
            compact_elements.append(item)

        extracted_pages.append({
            "url": p_url,
            "title": p_title,
            "elements": compact_elements,
        })

    # Relevant navigation flows connecting the included pages
    relevant_nav = []
    seen_edges = set()
    for rel in relationships:
        f_norm = _normalize_path(rel.get("from") or rel.get("source") or "")
        t_norm = _normalize_path(rel.get("to") or rel.get("target") or "")
        if f_norm in included_urls and t_norm in included_urls:
            edge_key = (f_norm, t_norm)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                relevant_nav.append({
                    "from": rel.get("from") or rel.get("source"),
                    "to": rel.get("to") or rel.get("target"),
                    "action": rel.get("action") or rel.get("trigger") or "navigate",
                })

    return {
        "application_url": crawl_knowledge.get("application_url") or root_url,
        "page_title": crawl_knowledge.get("page_title"),
        "pages": extracted_pages,
        "navigation_flows": relevant_nav,
        "crawl_id": crawl_knowledge.get("crawl_id"),
    }


def map_test_case_steps_to_crawl_evidence(
    test_cases: list[dict[str, Any]] | list[Any],
    application_knowledge: dict[str, Any] | None,
) -> list[dict[str, Any]] | list[Any]:
    """
    Deterministic mapping stage AFTER Test Case generation and BEFORE script generation.
    For every UI-related TestStep:
    - identify target page
    - identify target element
    - identify verified locator
    - set:
      - step.target_page
      - step.target_element
      - step.target_locator
      - step.evidence_status
    Uses ONLY discovered crawl evidence. Does NOT invent selectors.
    If no valid evidence exists:
    - sets evidence_status = "unsupported_missing_evidence"
    """
    if not test_cases:
        return []

    # Extract all discovered pages and elements from knowledge
    root_url = ""
    discovered_pages: list[dict[str, Any]] = []
    discovered_elements: list[dict[str, Any]] = []

    if application_knowledge and isinstance(application_knowledge, dict):
        root_url = str(application_knowledge.get("application_url") or "")
        if application_knowledge.get("pages"):
            discovered_pages = list(application_knowledge["pages"])
        elif application_knowledge.get("application_map", {}).get("pages"):
            discovered_pages = list(application_knowledge["application_map"]["pages"])

        if application_knowledge.get("discovered_elements"):
            discovered_elements = list(application_knowledge["discovered_elements"])
        else:
            for p in discovered_pages:
                p_url = p.get("url") or root_url
                for el in p.get("elements", []):
                    if isinstance(el, dict):
                        el_copy = dict(el)
                        el_copy.setdefault("page_url", p_url)
                        discovered_elements.append(el_copy)

    if not root_url and discovered_pages:
        root_url = str(discovered_pages[0].get("url") or "")

    for tc in test_cases:
        is_model = hasattr(tc, "model_dump")
        steps = tc.steps if is_model else (tc.get("steps") or [])
        case_unsupported_reasons: list[str] = []
        ui_mappings: list[dict[str, Any]] = []
        current_page = str(getattr(tc, "page_url", None) or (tc.get("page_url") if isinstance(tc, dict) else None) or root_url or "")

        for idx, step in enumerate(steps):
            is_step_model = hasattr(step, "model_dump")
            action = str(getattr(step, "action", None) if is_step_model else step.get("action") or "").strip()
            action_lower = action.lower()
            step_num = getattr(step, "step_number", idx + 1) if is_step_model else step.get("step_number", idx + 1)

            # If application knowledge was completely absent
            if not application_knowledge or (not discovered_pages and not discovered_elements and not root_url):
                step_target_page = None
                step_target_elem = None
                step_target_loc = None
                step_evidence_status = "unsupported_missing_evidence"
                case_unsupported_reasons.append(f"Step {step_num}: No crawl knowledge available for '{action}'")
            else:
                # 1. Check if navigation step
                is_nav = any(verb in action_lower for verb in ("navigate", "open", "go to", "visit", "launch"))
                if is_nav:
                    matched_page = None
                    for p in discovered_pages:
                        p_url = str(p.get("url") or "")
                        p_title = str(p.get("title") or "")
                        p_norm = _normalize_path(p_url)
                        if (p_norm != "/" and p_norm.lower() in action_lower) or (p_title and p_title.lower() in action_lower):
                            matched_page = p
                            break
                    if not matched_page:
                        # Dynamic token overlap matching between navigation action and discovered pages
                        action_tokens = _meaningful_tokens(action)
                        best_overlap = 0
                        for p in discovered_pages:
                            p_url = str(p.get("url") or "")
                            p_title = str(p.get("title") or "")
                            p_tokens = _meaningful_tokens(p_url + " " + p_title)
                            overlap = len(action_tokens & p_tokens)
                            if overlap > best_overlap:
                                best_overlap = overlap
                                matched_page = p
                    if not matched_page:
                        if any(k in action_lower for k in ("base", "home", "portal", "application", "dashboard", "root", "start")):
                            matched_page = next((p for p in discovered_pages if _normalize_path(str(p.get("url", ""))) == _normalize_path(root_url)), None)

                    target_url = str(matched_page.get("url")) if matched_page else root_url
                    if target_url:
                        step_target_page = target_url
                        step_target_elem = "page"
                        step_target_loc = f'page.goto("{target_url}")'
                        step_evidence_status = "verified"
                        current_page = target_url
                    else:
                        step_target_page = None
                        step_target_elem = None
                        step_target_loc = None
                        step_evidence_status = "unsupported_missing_evidence"
                        case_unsupported_reasons.append(f"Step {step_num}: Navigation target '{action}' not found in crawl pages")
                else:
                    step_tokens = set(re.findall(r"[a-zA-Z0-9]{2,}", action.lower()))
                    step_tokens.update(re.findall(r"[a-zA-Z0-9]{2,}", re.sub(r"[-_]", "", action.lower())))
                    quoted_matches = re.findall(r"['\"]([^'\"]+)['\"]", action)
                    for q in quoted_matches:
                        step_tokens.update(re.findall(r"[a-zA-Z0-9]{2,}", q.lower()))

                    best_score = 0
                    best_elem = None
                    best_page_url = current_page

                    for el in discovered_elements:
                        el_page = str(el.get("page_url") or root_url)
                        el_identity = " ".join(filter(None, [
                            str(el.get("name") or ""),
                            str(el.get("accessible_name") or ""),
                            str(el.get("label") or ""),
                            str(el.get("placeholder") or ""),
                            str(el.get("test_id") or ""),
                            str(el.get("element_id") or ""),
                        ]))
                        el_tokens = set(re.findall(r"[a-zA-Z0-9]{2,}", el_identity.lower()))
                        el_tokens.update(re.findall(r"[a-zA-Z0-9]{2,}", re.sub(r"[-_]", "", el_identity.lower())))
                        overlap = step_tokens & el_tokens

                        el_name = str(el.get("name") or el.get("accessible_name") or el.get("label") or el.get("test_id") or "")
                        clean_el_name = re.sub(r"[-_]", "", el_name.lower())
                        clean_action = re.sub(r"[-_]", "", action_lower)

                        has_substring = bool(
                            (el_name and len(el_name) >= 3 and (el_name.lower() in action_lower or clean_el_name in clean_action))
                            or any(token in action_lower for token in el_tokens if len(token) >= 4 and token not in ("input", "button", "page"))
                        )
                        has_quoted = any(q.lower() in el_identity.lower() or el_identity.lower() in q.lower() for q in quoted_matches) if quoted_matches else False

                        if not overlap and not has_substring and not has_quoted:
                            continue

                        score = len(overlap) * 2
                        # Proximity bonus for current page
                        if _normalize_path(el_page) == _normalize_path(current_page):
                            score += 3

                        if has_substring:
                            score += 8
                        if has_quoted:
                            score += 10

                        if score > best_score and score >= 2:
                            best_score = score
                            best_elem = el
                            best_page_url = el_page

                    if best_elem:
                        elem_name = best_elem.get("name") or best_elem.get("accessible_name") or best_elem.get("label") or best_elem.get("test_id") or "element"
                        locator = _extract_element_locator(best_elem)
                        step_target_page = best_page_url
                        step_target_elem = elem_name
                        step_target_loc = locator
                        step_evidence_status = "verified"
                        current_page = best_page_url
                    elif any(token in action_lower for token in ("url", "title", "visible", "loaded", "displayed", "redirect")) and any(verb in action_lower for verb in ("verify", "assert", "expect", "check", "ensure")):
                        # Verifiable page loaded/presence assertion
                        step_target_page = current_page
                        step_target_elem = "page"
                        step_target_loc = "expect(page).to_be_visible()"
                        step_evidence_status = "verified"
                    else:
                        step_target_page = None
                        step_target_elem = None
                        step_target_loc = None
                        step_evidence_status = "unsupported_missing_evidence"
                        case_unsupported_reasons.append(f"Step {step_num}: No discovered element in crawl evidence matches '{action}'")

            if is_step_model:
                step.target_page = step_target_page
                step.target_element = step_target_elem
                step.target_locator = step_target_loc
                step.evidence_status = step_evidence_status
            else:
                step["target_page"] = step_target_page
                step["target_element"] = step_target_elem
                step["target_locator"] = step_target_loc
                step["evidence_status"] = step_evidence_status

            ui_mappings.append({
                "step_number": step_num,
                "action": action,
                "target_page": step_target_page,
                "target_element": step_target_elem,
                "target_locator": step_target_loc,
                "evidence_status": step_evidence_status,
            })

        final_status = "unsupported_missing_evidence" if case_unsupported_reasons else "verified"

        if is_model:
            tc.ui_mapping = ui_mappings
            tc.evidence_status = final_status
            if hasattr(tc, "unsupported_evidence_reasons"):
                tc.unsupported_evidence_reasons = list(set((getattr(tc, "unsupported_evidence_reasons") or []) + case_unsupported_reasons))
        else:
            tc["ui_mapping"] = ui_mappings
            tc["evidence_status"] = final_status
            if case_unsupported_reasons:
                existing = tc.get("unsupported_evidence_reasons") or []
                tc["unsupported_evidence_reasons"] = list(set(existing + case_unsupported_reasons))

    return test_cases
