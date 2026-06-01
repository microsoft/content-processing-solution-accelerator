# Modifying System Processing Prompts

System prompts are used for processing steps in the pipeline. These prompts control how AI models extract, map, and evaluate content from documents.

## Document Processing Pipeline Prompts

The document processing pipeline uses system prompts for the mapping step, located at:
> [/src/ContentProcessor/src/libs/pipeline/handlers/map_handler.py](/src/ContentProcessor/src/libs/pipeline/handlers/map_handler.py)

## Claim Processing Workflow Prompts

The claim processing workflow uses additional prompts for RAI safety classification, summarization, and gap analysis stages. These prompts are executed by the Agent Framework Workflow Engine's `RAIExecutor`, `SummarizeExecutor`, and `GapExecutor`. For details on how they fit into the workflow, see [Claim Processing Workflow](./ClaimProcessWorkflow.md).

- **Responsible AI (RAI) prompts**: Located in the RAI step of the workflow:
  > [/src/ContentProcessorWorkflow/src/steps/rai/prompt/](/src/ContentProcessorWorkflow/src/steps/rai/prompt/)

- **Summarization prompts**: Located in the summarize step of the workflow:
  > [/src/ContentProcessorWorkflow/src/steps/summarize/prompt/](/src/ContentProcessorWorkflow/src/steps/summarize/prompt/)

- **Gap Analysis prompts**: Located in the gap analysis step of the workflow:
  > [/src/ContentProcessorWorkflow/src/steps/gap_analysis/prompt/](/src/ContentProcessorWorkflow/src/steps/gap_analysis/prompt/)

## Responsible AI (RAI) Safety Classifier

The RAI step acts as a **safety gate** between document extraction and summarization. It sends all extracted document text to an LLM-based classifier that evaluates content against 10 safety rules (self-harm, violence, illegal activities, discrimination, prompt injection, etc.).

The prompt is located at:
> [/src/ContentProcessorWorkflow/src/steps/rai/prompt/rai_executor_prompt.txt](/src/ContentProcessorWorkflow/src/steps/rai/prompt/rai_executor_prompt.txt)

The classifier returns a structured `RAIResponse` with:

- `IsNotSafe` (boolean) — whether any rule was violated
- `Reasoning` (string) — explanation of which rule(s) were violated

If `IsNotSafe` is `true`, the workflow **halts immediately** and the claim is marked as `Failed`. To customize what is considered unsafe, edit the numbered rules in `rai_executor_prompt.txt`.

---

## Gap Analysis Rules DSL

In addition to the prompt template, the gap analysis stage uses a **YAML-based Domain-Specific Language (DSL)** to define both types of gap rules — missing document checks and cross-document discrepancy detection. The rules file (`fnol_gap_rules.dsl.yaml`) is injected into the prompt at the `{{RULES_DSL}}` placeholder — domain experts can add, modify, or replace rules without writing code.

The DSL supports:

- **Missing document rules** — conditional requirements with a lightweight expression language (`when: "loss_type in [theft, burglary]"`)
- **Discrepancy rules** — cross-document field comparison with optional numeric tolerance
- **Document type registry** — maps logical types to extraction schemas
- **Canonical input fields** — typed fields the LLM infers from extracted data

For the complete DSL reference, expression language, domain adaptation examples, and writing guidelines, see [Gap Analysis Ruleset Guide](./GapAnalysisRulesetGuide.md).

## Schema-Specific Prompts

Schema-specific prompts are managed directly in the individual schema JSON file. The field descriptions in your schema act as prompts for the LLM during data extraction and mapping. See [Customizing Schema and Data](./CustomizeSchemaData.md) for details on how to write effective field descriptions.
