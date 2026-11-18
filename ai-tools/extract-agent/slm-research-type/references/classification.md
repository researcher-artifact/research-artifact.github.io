# Research type and evaluation method: classification guide

This guide defines how the agent fills, for each study, the six research-type criteria (`C1` to `C6`), the `Research Method` column and the `Evaluation Type` column of the `Data Extraction` sheet of DEF_TA.

## 1. What the two columns mean in DEF_TA

The article lists "research method and research-type criteria [Wieringa et al. 2006; Petersen et al. 2015], evaluation type" among the DEF fields (section *Data extraction*), and the workbook uses the columns as follows:

| DEF_TA column | Facet | Closed set of values | Methodological basis |
|---|---|---|---|
| `C1` to `C6` | Conditions of the decision table | True or False, each with a justification | Petersen et al. (2015), Table 7 |
| `Research Method` | **Research type** of the paper | Evaluation research; Validation research; Solution proposal; Philosophical paper; Opinion paper; Experience paper | Wieringa et al. (2006); Petersen et al. (2015) |
| `Evaluation Type` | **Empirical method** used to evaluate the solution | the ten methods of section 5, or `-` | Petersen et al. (2015), Fig. 19, with the method definitions of Easterbrook et al. (2008) and Wohlin et al. (2012) |

Keep these meanings even though the column names may suggest the opposite: the 153 studies already coded use them this way, and the agreement between raters (Fleiss' kappa) is computed column by column.

## 2. Research types (Wieringa et al., 2006)

| Research type | Definition (Wieringa et al., 2006, section 3) |
|---|---|
| **Evaluation research** | Investigation of a technique **in practice**: the technique is implemented in practice and evaluated there, showing how it works and what its benefits and drawbacks are. Causal properties are studied empirically, "such as by case study, field study, field experiment, survey". |
| **Validation research** | Investigation of the properties of a novel technique that **has not yet been implemented in practice**. The investigation uses "a thorough, methodologically sound research setup", such as "experiments, simulation, prototyping, mathematical analysis, mathematical proof of properties". |
| **Solution proposal** | A solution is proposed and its potential benefits and applicability are argued, for example with a small example or a sound argument, but **without a full empirical evaluation**. |
| **Philosophical paper** | Sketches a new way of looking at things: a new conceptual framework, taxonomy or structure of the field, without proposing and investigating a solution. |
| **Opinion paper** | Expresses the authors' opinion on whether a technique is good or bad or how things should be done, without relying on research methods. |
| **Experience paper** | Reports the authors' personal experience of what was done in practice and how it worked out; written from the practitioner's perspective, without a research method. |

Petersen et al. (2015, p. 12) stress the distinction that caused most inconsistency between raters: "Both have to be empirically evaluated, however, validation is not used in practice (i.e. it is done in the lab), while evaluation studies take place in a real-world industrial context. Furthermore, a new solution may be reported to be used in practice, though it is still a solution proposal if the empirical evaluation is missing."

## 3. The six criteria (C1 to C6)

Answer each criterion from the full text and justify it in one or two sentences, citing the section or page. Do not infer a True from the title or the abstract alone.

| Code | Criterion | True when | False when |
|---|---|---|---|
| **C1** | Used in practice | The proposed solution is deployed or operated in a **real-world setting**: a company, hospital, court, public agency or other organisation uses it with real users or real operational data. | The solution exists only as a design, a prototype, a laboratory deployment, a local or public **testnet** (Ganache, Ropsten, Sepolia, Hyperledger test network), a container cluster set up by the authors, or a simulation, even if it is fully implemented. |
| **C2** | Novel solution | The study proposes a new technique, scheme, architecture, protocol, model or tool, or a substantial extension of an existing one. | The study applies, compares or reports an existing solution without a new contribution of its own. |
| **C3** | Empirical evaluation | The study investigates the solution with one of the methods of section 5: measurements, experiments or benchmarks, a simulation, a working prototype run and tested by the authors, a formal proof of the solution's properties as the main evaluation, a case study or a survey. | The solution is only described and argued for: an illustrative scenario or worked example on paper, a feature comparison table or a qualitative security discussion, without running or formally analysing the solution. Easterbrook et al. (2008, section 5.2) warn that "case study" is often used to mean a worked example; a worked example is not an empirical evaluation. |
| **C4** | Evaluated in practice | The empirical evaluation itself takes place **in the real-world setting of C1**, with practitioners, real users or real operational data of an organisation. | The evaluation is done in a laboratory, testnet, simulator or with synthetic, public benchmark or student data. |
| **C5** | Conceptual framework | The main contribution is a new conceptual framework, taxonomy, reference model or way of looking at the problem. | The conceptual model is only the design of a concrete solution that is then proposed or evaluated. |
| **C6** | Opinion or authors' experience | The paper rests on the authors' opinion (start the justification with `Opinion:`) or on their personal experience in practice (start the justification with `Experience:`), not on a research method. | The paper relies on design, analysis or empirical work. |

Implementation is not the same as use in practice. A prototype that runs on the authors' machines or on a testnet is implemented, but it is not used in practice (C1 False) and its evaluation is not in practice (C4 False).

## 4. Decision table

The tool applies the decision table of Petersen et al. (2015, Table 7), with C4 making explicit that the evaluation of an evaluation-research paper takes place in practice. The rules are checked in this order and the first that applies gives the research type:

| Rule | Condition | Research type |
|---|---|---|
| R6 | C6 True (opinion), C1, C2 and C3 False | Opinion paper |
| R3 | C6 True (experience), C1 True, C2 and C3 False | Experience paper |
| R1 | C3 True and C4 True (so C1 True) | Evaluation research |
| R4 | C3 True, C4 False and C1 False | Validation research |
| R2 | C3 False and C2 True | Solution proposal |
| R5 | C3 False, C2 False and C5 True | Philosophical paper |

Consistency rules enforced by the `validate` command:

- C4 True requires C1 True and C3 True.
- C6 True excludes C3 True.
- C1 True, C3 True and C4 False is contradictory: if the solution is used in practice and the evaluation investigates that use, C4 is True; if the evaluation was carried out in a laboratory, C1 is False.
- The value of `Research Method` must equal the type given by the table.

## 5. Evaluation methods (Evaluation Type)

Use exactly one of the labels below, or `-` when the research type has no empirical evaluation (Solution proposal, Philosophical paper, Opinion paper, Experience paper). Petersen et al. (2015, Fig. 19) assign each method to evaluation or validation research; the method must agree with the research type.

### Methods of evaluation research (in practice)

| Label | Definition |
|---|---|
| **Industrial case study** | "An empirical inquiry that investigates a contemporary phenomenon within its real-life context" (Yin, cited by Easterbrook et al., 2008, section 5.2): the solution is studied in use in one or more real organisations, with data collected from that context. Wohlin et al. (2012, ch. 2) describe case studies as observational studies of a project or activity in its real setting. |
| **Controlled experiment with practitioners** | "An investigation of a testable hypothesis where one or more independent variables are manipulated to measure their effect on one or more dependent variables" (Easterbrook et al., 2008, section 5.1), in which the **subjects are practitioners** (for example clinicians, analysts, auditors or developers of the target organisation). Machines or students as subjects are not practitioners. |
| **Practitioner-targeted survey** | Survey research (Easterbrook et al., 2008, section 5.3; Wohlin et al., 2012, ch. 2): a questionnaire or structured interviews with a defined population of practitioners to evaluate the solution or its use. |
| **Action research** | The researchers intervene in a real organisation to solve a problem with the solution and study the effects of the change (Easterbrook et al., 2008, section 5.5). |
| **Ethnography** | Prolonged observation of a community of practice to understand how the solution is used (Easterbrook et al., 2008, section 5.4). |

### Methods of validation research (not in practice)

| Label | Definition |
|---|---|
| **Laboratory experiment (machine or human)** | A controlled experiment carried out in the laboratory: independent variables (file size, number of users or attributes, key length, number of nodes, attack type) are varied and dependent variables (time, gas cost, throughput, latency, accuracy, detection rate, robustness) are measured, usually against baselines. Wohlin et al. (2012, ch. 2) call these technology-oriented experiments when the treatments are applied to objects such as programs or systems, and human-oriented experiments when the subjects are people (for example students). Benchmarks of a prototype on a local network, a testnet or a cloud instance set up by the authors belong here. |
| **Simulation as an empirical method** | The behaviour of the solution or of its environment is reproduced in a simulation model or simulator (for example NS-3, OMNeT++, MATLAB, CloudSim or a simulated network of nodes) rather than measured on a working implementation of the solution. |
| **Prototyping** | A working prototype is built and its feasibility is demonstrated (proof of concept, functional tests, screenshots of the interface, use-case walkthroughs), without systematic manipulation of variables or measurement against hypotheses. |
| **Mathematical analysis and proof of properties** | The main evaluation is analytical: formal security proofs (for example under the random oracle model or with BAN logic, ProVerif or Tamarin), complexity or cost analysis, or theorem proofs. |
| **Academic case study** | A case study in an academic setting, for example with students, a university system or a research laboratory used as the case, rather than an industrial organisation. |

### When a study uses several methods

Record the **principal** method: the one on which the authors base their main evaluation claims (usually the section titled *Evaluation*, *Experiments*, *Results* or *Performance analysis*). If two methods carry equal weight, take the one listed first in the tables above. Name the other methods in the justification of C3, for example: "True. Justification: Section 6 measures encryption and gas costs on a private Ethereum network for 1 to 50 MB files (laboratory experiment); Section 5 also gives a security proof."

## 6. Calibration examples

| Study pattern | C1 C2 C3 C4 C5 C6 | Research Method | Evaluation Type |
|---|---|---|---|
| Blockchain EHR sharing scheme, smart contracts deployed on Ganache, gas cost and latency measured for different numbers of records | F T T F F F | Validation research | Laboratory experiment (machine or human) |
| Watermarking scheme, robustness against JPEG compression and cropping measured on a public image dataset (PSNR, NC) | F T T F F F | Validation research | Laboratory experiment (machine or human) |
| Access-control protocol evaluated in NS-3 with simulated vehicles | F T T F F F | Validation research | Simulation as an empirical method |
| Framework implemented as a web prototype; the paper shows the screens and a walkthrough of the use cases, no measurements | F T T F F F | Validation research | Prototyping |
| Signcryption scheme with a security proof under the random oracle model and a theoretical cost comparison only | F T T F F F | Validation research | Mathematical analysis and proof of properties |
| Insider-threat detection deployed in a bank; detection results reported over six months of real logs | T T T T F F | Evaluation research | Industrial case study |
| Tool used by forensic analysts of a police unit in a controlled task, with time and accuracy measured | T T T T F F | Evaluation research | Controlled experiment with practitioners |
| Architecture described with diagrams and an illustrative scenario, no implementation or measurement | F T F F F F | Solution proposal | - |
| Taxonomy of tracking architectures, no solution proposed | F F F F T F | Philosophical paper | - |
| Position paper arguing that courts should adopt blockchain evidence logs | F F F F F T (`Opinion: ...`) | Opinion paper | - |

## 7. Note on the existing codings

In the 153 studies coded before this agent, C1 was often recorded as True for solutions that were implemented and tested in a laboratory or testnet, and those studies were classified as Evaluation research (for example "True. Justification: The proposed system is implemented and tested on Ethereum test chain"). Under the definitions of Wieringa et al. (2006) and Petersen et al. (2015) adopted here, such studies are Validation research. The agent applies the definitions above; when it codes a study that already has R1 values, a disagreement on this point is expected and should be reported to Researcher 1 rather than resolved by imitating the earlier coding.

## References

- Easterbrook, S., Singer, J., Storey, M.-A., Damian, D. (2008). Selecting empirical methods for software engineering research. In F. Shull, J. Singer, D. Sjøberg (eds.), *Guide to Advanced Empirical Software Engineering*, Springer, 285–311.
- Petersen, K., Vakkalanka, S., Kuzniarz, L. (2015). Guidelines for conducting systematic mapping studies in software engineering: an update. *Information and Software Technology* 64, 1–18.
- Wieringa, R., Maiden, N., Mead, N., Rolland, C. (2006). Requirements engineering paper classification and evaluation criteria: a proposal and a discussion. *Requirements Engineering* 11(1), 102–107.
- Wohlin, C., Runeson, P., Höst, M., Ohlsson, M. C., Regnell, B., Wesslén, A. (2012). *Experimentation in Software Engineering*. Springer.
