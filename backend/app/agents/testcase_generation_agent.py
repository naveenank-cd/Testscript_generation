import json

from app.agents.base_agent import BaseAgent, ExecutionContext
from app.llm.client import build_llm_client
from app.llm.context import batches, scoped_context
from app.core.config import settings
from app.llm.prompt_loader import PromptLoader
from app.schemas.context_schema import StructuredContext
from app.schemas.scenario_schema import ScenarioBatch
from app.schemas.testcase_schema import TestCase, TestCaseBatch
from app.utils.similarity import similarity
from collections import defaultdict


def deduplicate_test_cases(test_cases: list[TestCase]) -> list[TestCase]:
    unique: list[TestCase] = []
    seen_case_ids = set()
    for tc in test_cases:
        tc_case_id = str(tc.test_case_id)
        if tc_case_id in seen_case_ids:
            continue
        is_duplicate = False
        for existing in unique:
            if str(tc.test_case_id) == str(existing.test_case_id):
                is_duplicate = True
                break
            if str(tc.scenario_id) == str(existing.scenario_id):
                title_sim = similarity(tc.title, existing.title)
                desc_sim = similarity(tc.description, existing.description)
                if title_sim >= 0.88 or (title_sim >= 0.75 and desc_sim >= 0.85):
                    is_duplicate = True
                    break
        if not is_duplicate:
            unique.append(tc)
            seen_case_ids.add(tc_case_id)
    return unique


class TestCaseGenerationAgent(BaseAgent[TestCaseBatch]):
    output_model = TestCaseBatch

    def __init__(self, llm_client=None, prompt_loader=None):
        super().__init__(llm_client=llm_client)
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader or PromptLoader()

    async def run(self, input_data, execution_context: ExecutionContext) -> TestCaseBatch:
        scenarios = ScenarioBatch.model_validate({"scenarios": input_data["scenarios"]})
        context = None
        if input_data.get("context"):
            context = StructuredContext.model_validate(input_data["context"])
        template = "testcase_regeneration.jinja2" if "validation" in input_data else "testcase_generation.jinja2"
        task = "regeneration" if "validation" in input_data else "generation"
        client = self.llm_client or build_llm_client(
            task, mock_mode=execution_context.metadata.get("mock_mode")
        )
        context_dict = context.model_dump(mode="json") if context else {}
        scenario_items = scenarios.model_dump(mode="json")["scenarios"]
        existing = input_data.get("existing_test_cases", [])

        async def generate_batch(selected):
            compact_context = scoped_context(context_dict, selected) if context else {}
            scenario_ids = {str(item["scenario_id"]) for item in selected}
            related_existing = [
                item for item in existing if str(item.get("scenario_id")) in scenario_ids
            ]
            scenario_batch = {"scenarios": selected}
            user_prompt = self.prompt_loader.render(
                template,
                scenarios=json.dumps(scenario_batch, ensure_ascii=False),
                context=json.dumps(compact_context, ensure_ascii=False),
                failed_item=json.dumps(related_existing, ensure_ascii=False),
                scenario=json.dumps(scenario_batch, ensure_ascii=False),
                feedback=json.dumps(input_data.get("validation", {}), ensure_ascii=False),
            )
            return await client.generate_structured_output(
                system_prompt="You are a senior software test engineer. Return schema-compliant JSON only.",
                user_prompt=user_prompt,
                response_model=TestCaseBatch,
                request_id=execution_context.request_id,
            )

        generated = []
        for batch in batches(scenario_items, settings.llm_testcase_batch_size):
            result = await generate_batch(batch)
            by_scenario = defaultdict(list)
            for idx, test_case in enumerate(result.test_cases):
                sc_id = str(test_case.scenario_id)
                matched_scenario = next((s for s in batch if str(s["scenario_id"]) == sc_id), None)
                if matched_scenario:
                    by_scenario[sc_id].append(test_case)
                elif idx < len(batch):
                    target_sc_id = str(batch[idx]["scenario_id"])
                    test_case.scenario_id = batch[idx]["scenario_id"]
                    if "project_id" in batch[idx]:
                        test_case.project_id = batch[idx]["project_id"]
                    by_scenario[target_sc_id].append(test_case)
            for scenario in batch:
                scenario_id = str(scenario["scenario_id"])
                if not by_scenario[scenario_id]:
                    singleton = await generate_batch([scenario])
                    matches = [
                        case for case in singleton.test_cases
                        if str(case.scenario_id) == scenario_id
                    ]
                    if not matches and singleton.test_cases:
                        for case in singleton.test_cases:
                            case.scenario_id = scenario["scenario_id"]
                            if "project_id" in scenario:
                                case.project_id = scenario["project_id"]
                        matches = singleton.test_cases
                    if not matches:
                        raise ValueError(f"LLM did not return a complete test case for scenario {scenario_id}")
                    by_scenario[scenario_id].extend(matches)
            ordered = [tc for scenario in batch for tc in by_scenario[str(scenario["scenario_id"])]]
            for test_case in ordered:
                source_scenario = next(item for item in batch if str(item["scenario_id"]) == str(test_case.scenario_id))
                for field in ("requirement_ids", "acceptance_criteria_ids", "user_story_ids", "feature_ids"):
                    available = [str(value) for value in source_scenario.get(field, [])]
                    mapped = [str(value) for value in getattr(test_case, field, []) if str(value) in set(available)]
                    setattr(test_case, field, list(dict.fromkeys(mapped or available)))
                if hasattr(test_case, "unsupported_evidence_reasons"):
                    scenario_reasons = source_scenario.get("unsupported_evidence_reasons", [])
                    test_case.unsupported_evidence_reasons = list(dict.fromkeys((test_case.unsupported_evidence_reasons or []) + scenario_reasons))
                test_case.source_references=list(dict.fromkeys((test_case.source_references or [str(test_case.scenario_id)])+[str(x) for x in context_dict.get("image_ids",[])]))
            generated.extend(ordered)
        return TestCaseBatch(test_cases=deduplicate_test_cases(generated))
