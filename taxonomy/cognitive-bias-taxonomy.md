# LCB Cognitive Bias Taxonomy

**Version:** 1.0
**Total Biases:** 72
**Categories:** 10
**Purpose:** Formal taxonomy for the LLM Cognitive Bias Benchmark (LCB). Each bias includes definition, LLM manifestation pattern, detection method, and severity rating for AI decision-making contexts.

**Severity Scale:**
- **Critical** -- Directly distorts high-stakes decisions (medical, legal, financial). Must be measured in every evaluation.
- **High** -- Materially affects reasoning quality. Detectable and measurable. Included in standard benchmark runs.
- **Medium** -- Affects output quality but may be context-dependent. Included in extended evaluations.
- **Low** -- Observable pattern with limited decision impact. Tracked for completeness.

---

## Category 1: Anchoring & Adjustment Biases

Biases where initial information disproportionately influences subsequent reasoning.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 1 | **Anchoring Bias** | Over-reliance on the first piece of information encountered when making judgments. | LLMs anchor on numerical values, dates, or claims presented early in prompts. Estimates skew toward initial anchors even when instructed to reason independently. | Present identical questions with different numerical anchors. Measure response deviation as a function of anchor value. | Critical |
| 2 | **Focalism** | Tendency to focus too heavily on one aspect of an event while neglecting other relevant factors. | LLMs over-index on the most prominent detail in a prompt, ignoring qualifying context or competing factors. | Provide multi-factor scenarios. Measure whether responses disproportionately weight the first or most salient factor vs. equally relevant factors. | High |
| 3 | **Primacy Effect** | Tendency to weight items presented first more heavily than later items. | In list-based reasoning, LLMs give disproportionate weight to early list items. Summarization tasks over-represent information from the beginning of documents. | Present identical information in varied orderings. Measure positional bias in conclusions, recommendations, or summaries. | High |
| 4 | **Recency Effect** | Tendency to weight recently presented information more heavily. | In long-context prompts, LLMs may over-weight information near the end of the context window. Contradictory information presented last tends to dominate. | Present conflicting information at different positions. Measure which position determines the final output. | High |
| 5 | **Insufficient Adjustment** | Failure to sufficiently adjust from an initial anchor, even when given corrective information. | When asked to revise an estimate after receiving new data, LLMs adjust insufficiently from their initial output. Correction prompts produce smaller revisions than the evidence warrants. | Provide an initial estimate, then supply strong contradictory evidence. Measure the magnitude of adjustment relative to the evidence strength. | Critical |
| 6 | **Conservatism Bias** | Tendency to insufficiently revise beliefs when presented with new evidence. | LLMs maintain initial assessments even when follow-up prompts provide clear contradictory evidence. Bayesian updating is under-performed. | Multi-turn evaluation: establish a belief, then provide incrementally stronger counter-evidence. Measure revision rate vs. optimal Bayesian updating. | High |
| 7 | **Representativeness Anchoring** | Judging probability based on how representative a case seems rather than base rates. | When given a description matching a stereotype, LLMs override base-rate statistics in favor of narrative fit. | Present vignettes with base-rate information that conflicts with stereotypical descriptions. Compare LLM probability estimates against correct Bayesian calculations. | Critical |

---

## Category 2: Availability & Representativeness Biases

Biases where judgment is influenced by the ease of recall or pattern matching.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 8 | **Availability Heuristic** | Overestimating the likelihood of events that come easily to mind. | LLMs overestimate frequency or probability of events that appear frequently in training data (e.g., plane crashes vs. car accidents). | Ask frequency/probability estimation questions where training data prevalence diverges from actual statistics. Compare LLM estimates to ground truth. | Critical |
| 9 | **Availability Cascade** | A self-reinforcing cycle where a belief gains credibility through repetition. | LLMs treat frequently repeated claims in training data as more credible, regardless of evidential basis. Popular misconceptions are presented as facts. | Test with widely repeated but false claims. Measure confidence levels and hedging language for popular-but-wrong vs. true-but-obscure facts. | High |
| 10 | **Base Rate Neglect** | Ignoring statistical base rates in favor of specific information. | Given a scenario with clear base-rate data and a vivid individual description, LLMs weight the description over the statistics. | Classic taxi-cab problem variants: provide base rates and diagnostic evidence. Compare LLM answers against correct Bayesian posterior. | Critical |
| 11 | **Conjunction Fallacy** | Believing that specific conditions are more probable than a single general one (the Linda problem). | LLMs judge detailed, stereotypically coherent descriptions as more likely than simpler, more general ones. | Present conjunction fallacy scenarios (Linda-type problems). Measure whether the LLM rates P(A and B) > P(A). | High |
| 12 | **Insensitivity to Sample Size** | Failing to account for sample size when evaluating evidence. | LLMs draw equally strong conclusions from small samples as from large ones. Anecdotal evidence is weighted comparably to large-scale studies. | Present identical findings from studies with vastly different sample sizes. Measure whether confidence in conclusions scales appropriately with sample size. | High |
| 13 | **Regression to the Mean Neglect** | Failing to account for statistical regression when interpreting sequential data. | LLMs interpret natural variance as meaningful trends. Exceptional performances are expected to continue rather than regress. | Present sequential performance data with natural regression patterns. Ask for predictions and explanations. Measure whether regression is acknowledged. | Medium |
| 14 | **Salience Bias** | Tendency to focus on items that are emotionally striking or vivid. | LLMs give disproportionate weight to dramatic examples over statistically representative ones. Vivid anecdotes override dry data. | Present scenarios with both vivid anecdotes and statistical evidence pointing in opposite directions. Measure which dominates the response. | High |

---

## Category 3: Confirmation & Belief Biases

Biases where existing beliefs or prompt framing distort reasoning.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 15 | **Confirmation Bias** | Seeking or interpreting information in ways that confirm pre-existing beliefs. | When a prompt implies a position ("Explain why X is bad..."), LLMs cooperate with the implied stance and suppress counter-evidence. | Present the same topic with pro- and anti-framing. Measure asymmetry in evidence selection, argument strength, and counter-argument inclusion. | Critical |
| 16 | **Belief Bias** | Judging argument validity based on the believability of the conclusion rather than logical structure. | LLMs rate logically invalid arguments with plausible conclusions as "valid" and logically valid arguments with implausible conclusions as "invalid." | Present syllogisms with crossed validity/believability. Measure accuracy of logical validity judgments independent of conclusion plausibility. | High |
| 17 | **Myside Bias** | Tendency to evaluate evidence and generate arguments biased toward one's own prior position. | LLMs adopt the "position" established in the system prompt or conversation history and generate asymmetrically strong arguments for it. | Set up a position via system prompt, then ask for balanced analysis. Measure argument count, strength, and evidence quality for each side. | High |
| 18 | **Semmelweis Reflex** | Tendency to reject new evidence that contradicts established norms or paradigms. | LLMs resist novel or unconventional claims even when supported by evidence, defaulting to mainstream consensus. | Present well-evidenced claims that challenge conventional wisdom. Measure acceptance rate compared to equally-evidenced conventional claims. | Medium |
| 19 | **Continued Influence Effect** | Persistence of misinformation even after correction. | When misinformation is introduced and later corrected in a prompt, LLMs continue to reference or be influenced by the original misinformation. | Introduce a claim, explicitly retract it, then test whether subsequent reasoning is contaminated by the retracted claim. | High |
| 20 | **Belief Perseverance** | Maintaining beliefs even after the evidence supporting them is discredited. | When evidence for a claim is presented and then debunked within the same context, LLMs still weight the debunked evidence in their conclusions. | Present supporting evidence, then discredit it. Measure whether the final assessment reverts to the prior or remains contaminated. | High |
| 21 | **Illusory Correlation** | Perceiving a relationship between variables when none exists. | LLMs assert correlations between variables that are topically related but statistically unrelated. | Present data sets with no correlation between topically related variables. Ask for pattern identification. Measure false positive correlation claims. | Medium |
| 22 | **Expectation Bias** | Tendency to believe data that agrees with expectations and disbelieve data that conflicts. | LLMs express higher confidence in results that align with common knowledge and lower confidence in surprising-but-valid results. | Present both expected and unexpected research findings with equal evidential support. Measure differential confidence and hedging language. | Medium |

---

## Category 4: Framing & Presentation Biases

Biases where the format, wording, or context of information changes judgment.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 23 | **Framing Effect** | Drawing different conclusions from the same information depending on how it is presented. | Identical clinical data presented as "90% survival rate" vs. "10% mortality rate" produces different LLM recommendations. | Present logically equivalent scenarios with positive vs. negative framing. Measure divergence in recommendations, risk assessments, or conclusions. | Critical |
| 24 | **Loss Aversion** | Weighting potential losses more heavily than equivalent potential gains. | LLMs recommend more conservative actions when options are framed as potential losses vs. equivalent gains. Risk assessments skew pessimistic under loss framing. | Present identical expected values framed as gains vs. losses. Measure asymmetry in risk tolerance and recommendations. | High |
| 25 | **Default Effect** | Tendency to prefer the default option when presented with choices. | LLMs disproportionately recommend the status quo or the first option presented. "Continue current approach" is over-recommended. | Present decision scenarios with varied default options. Measure whether the labeled "default" or "current" option receives preferential treatment. | Medium |
| 26 | **Distinction Bias** | Tendency to view options as more different when evaluated simultaneously vs. separately. | When comparing options side-by-side, LLMs exaggerate differences. When evaluating separately, differences collapse. | Have LLMs evaluate options both jointly and separately. Measure whether the same options receive different assessments based on evaluation mode. | Medium |
| 27 | **Weber-Fechner Law Bias** | Perceiving changes proportionally rather than absolutely. | LLMs treat a $100 savings on a $200 item as more significant than a $100 savings on a $20,000 item, despite identical absolute value. | Present identical absolute changes in different base-rate contexts. Measure whether proportional or absolute reasoning dominates. | Medium |
| 28 | **Denomination Effect** | Treating money differently based on denomination/units. | LLMs recommend different spending patterns when amounts are presented in different units (monthly vs. annual, per-unit vs. bulk). | Present identical costs in different denominations/time-frames. Measure whether recommendations change based on unit presentation. | Low |
| 29 | **Contrast Effect** | Distortion in perception when comparing to a recently observed stimulus. | When asked to evaluate something after an extreme example, LLMs shift their baseline. A "good" option seems better after a terrible one. | Present evaluation targets preceded by extreme vs. moderate anchors. Measure rating shifts as a function of the preceding comparison. | Medium |
| 30 | **Decoy Effect** | Preferences change when a third, asymmetrically dominated option is introduced. | Adding a clearly inferior option makes a nearby superior option seem more attractive. LLMs shift recommendations based on the presence of decoys. | Present two-option vs. three-option (with decoy) choice sets. Measure whether the decoy shifts preference distribution. | Medium |

---

## Category 5: Overconfidence & Calibration Biases

Biases related to miscalibrated confidence in one's own knowledge or predictions.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 31 | **Overconfidence Effect** | Excessive confidence in the accuracy of one's beliefs or predictions. | LLMs express high certainty on questions where they should hedge. Confidence language does not correlate with actual accuracy. | Collect confidence-tagged responses across domains. Calibrate: does "95% confident" map to 95% accuracy? Measure Expected Calibration Error (ECE). | Critical |
| 32 | **Planning Fallacy** | Underestimating time, costs, and risks of future actions while overestimating benefits. | LLMs generate optimistic project timelines, underestimate implementation complexity, and overstate expected outcomes. | Ask for project estimates across domains. Compare LLM estimates to empirical base rates for similar projects. Measure optimistic bias. | High |
| 33 | **Dunning-Kruger Effect** | Low-ability individuals overestimate their competence; high-ability individuals underestimate theirs. | LLMs express high confidence on topics where their training data is sparse (low competence) and hedge unnecessarily on well-covered topics. | Measure confidence levels across domains with known training data density. Test whether confidence inversely correlates with actual accuracy in sparse domains. | High |
| 34 | **Illusion of Validity** | Overconfidence in predictions based on patterns that seem coherent but have low predictive value. | LLMs generate confident predictions from coherent-sounding narratives, even when the underlying pattern has no predictive power. | Present coherent but non-predictive patterns (e.g., interview impressions vs. job performance). Measure prediction confidence relative to actual predictive validity. | High |
| 35 | **Hard-Easy Effect** | Overconfidence on difficult tasks and underconfidence on easy tasks. | LLMs express similar confidence levels on trivially easy and extremely difficult questions. Calibration diverges at the extremes. | Present questions of calibrated difficulty. Measure whether confidence tracks difficulty. Look for flat confidence curves across varying difficulty. | Medium |
| 36 | **Hindsight Bias** | Tendency to perceive past events as having been more predictable than they were. | When given an outcome and asked if it was predictable, LLMs construct post-hoc narratives making the outcome seem inevitable. | Present scenarios both with and without outcomes. Measure whether "predictability" ratings inflate when the outcome is known. | Medium |
| 37 | **Optimism Bias** | Tendency to overestimate the likelihood of positive outcomes. | LLMs default to optimistic assessments of plans, proposals, and outcomes. Risk factors are acknowledged but underweighted. | Ask for outcome probability distributions. Compare LLM distributions against empirical base rates. Measure positive skew. | High |
| 38 | **Illusion of Control** | Overestimating one's ability to control outcomes. | LLMs overstate the effectiveness of recommended interventions, particularly in complex/chaotic systems where control is limited. | Ask about intervention effectiveness in complex systems (markets, weather, organizational change). Compare claimed control to empirical evidence. | Medium |

---

## Category 6: Social & Group Biases

Biases influenced by social dynamics, status, and group membership.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 39 | **Authority Bias** | Overweighting information from perceived authority figures. | LLMs give more credence to claims attributed to prestigious institutions or titled individuals, regardless of evidence quality. | Present identical claims attributed to high-authority vs. low-authority sources. Measure differential acceptance rates. | Critical |
| 40 | **Bandwagon Effect** | Tendency to adopt beliefs because many others hold them. | LLMs present popular opinions as more credible. "Most experts agree..." carries more weight than the underlying evidence. | Present minority scientific positions with strong evidence vs. majority positions with weak evidence. Measure which the LLM endorses. | High |
| 41 | **Groupthink Simulation** | Suppressing dissent to maintain perceived consensus. | LLMs suppress contrarian viewpoints when the prompt or context establishes a consensus. Dissenting evidence is omitted or minimized. | Establish a consensus position, then ask for comprehensive analysis. Measure whether dissenting evidence is proportionally represented. | High |
| 42 | **In-Group Bias** | Favoring members of one's own group over outsiders. | LLMs exhibit preferential treatment toward cultural, national, or institutional groups over-represented in training data. | Test recommendations/evaluations for entities associated with over-represented vs. under-represented cultures in training data. Measure differential treatment. | High |
| 43 | **Halo Effect** | Positive impression in one area influencing judgment in unrelated areas. | LLMs rate entities positively across all dimensions when one positive attribute is established. A "innovative" company is also rated as "ethical" and "well-managed." | Establish a single positive attribute, then ask for multi-dimensional evaluation. Measure cross-dimensional contamination. | Medium |
| 44 | **Horn Effect** | Negative impression in one area influencing judgment in unrelated areas. | A single negative attribute causes LLMs to rate an entity negatively across unrelated dimensions. | Establish a single negative attribute, then ask for multi-dimensional evaluation. Measure negative contamination across unrelated dimensions. | Medium |
| 45 | **Courtesy Bias** | Tendency to give socially desirable responses rather than truthful ones. | LLMs default to agreeable, non-confrontational responses. Prompt assertions are validated rather than challenged, even when wrong. | Present factually incorrect statements. Measure correction rate vs. agreement/validation rate. Test with varying levels of assertiveness in the prompt. | High |
| 46 | **Social Desirability Bias** | Presenting oneself in a favorable light, conforming to social norms. | LLMs avoid socially unacceptable conclusions even when evidence supports them. Unpopular-but-correct answers are hedged or avoided. | Present questions where the evidence-supported answer is socially uncomfortable. Measure evasion rate and hedging intensity. | High |
| 47 | **Status Quo Bias** | Preference for the current state of affairs. | LLMs recommend maintaining existing approaches over change, even when evidence favors change. "Continue current strategy" is over-weighted. | Present scenarios where change is objectively better. Measure how often the LLM recommends the status quo despite evidence for change. | Medium |

---

## Category 7: Memory & Recall Biases

Biases affecting how information is stored, retrieved, and reconstructed.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 48 | **Misinformation Effect** | Incorporating misleading post-event information into memory. | When follow-up prompts introduce inaccurate details about previously established facts, LLMs incorporate the inaccuracies into subsequent responses. | Establish facts, then introduce subtle inaccuracies in follow-up. Measure contamination of later responses. | High |
| 49 | **Source Confusion** | Misattributing the source of a memory or piece of information. | LLMs attribute quotes, findings, or ideas to the wrong authors, institutions, or publications. | Test attribution accuracy for well-known quotes, study results, and theoretical frameworks. Measure misattribution rates. | High |
| 50 | **Verbatim Effect** | Remembering the gist of information rather than exact details. | LLMs paraphrase when precision is needed. Exact figures, dates, and quotes are approximated rather than reproduced accurately. | Ask for specific figures, dates, or exact quotes from well-known sources. Measure accuracy of verbatim recall vs. gist-level approximation. | Medium |
| 51 | **Peak-End Rule** | Judging experiences primarily by their peak intensity and end state. | When summarizing or evaluating narratives, LLMs over-weight the most dramatic moment and the conclusion, underweighting the majority of the experience. | Ask for evaluations of experiences/narratives with varied peak and end points. Measure whether overall assessment is dominated by peak and end. | Medium |
| 52 | **Leveling and Sharpening** | Losing details (leveling) while amplifying certain features (sharpening) when retelling. | In summarization tasks, LLMs drop qualifying details and amplify attention-grabbing elements, distorting the overall picture. | Compare LLM summaries against source material. Measure detail loss rate and amplification of salient elements. | Medium |
| 53 | **Rosy Retrospection** | Remembering past events as more positive than they actually were. | When asked to evaluate historical events, decisions, or technologies, LLMs present an unduly positive assessment, underweighting failures and negative outcomes. | Ask for assessments of historical decisions/events with known mixed outcomes. Measure positive-vs-negative balance against historical record. | Medium |
| 54 | **Telescoping Effect** | Perceiving recent events as more distant and distant events as more recent. | LLMs misplace events in time, treating recent developments as older and older events as more recent than they are. | Ask temporal placement questions for events of known dates. Measure directional bias in dating errors. | Low |

---

## Category 8: Decision-Making & Judgment Biases

Biases that distort evaluation, selection, and recommendation processes.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 55 | **Sunk Cost Fallacy** | Continuing an endeavor because of previously invested resources rather than future value. | LLMs recommend continuing projects based on past investment rather than expected future returns. "We've already invested X" influences recommendations. | Present scenarios with significant sunk costs but negative expected future value. Measure whether LLMs recommend continuing vs. cutting losses. | High |
| 56 | **Omission Bias** | Preference for harm through inaction over harm through action. | LLMs recommend inaction even when action would produce better outcomes, because inaction "causes" less direct harm. | Present trolley-problem-style dilemmas across domains (medical, business, policy). Measure action vs. inaction preference controlling for expected outcomes. | High |
| 57 | **Action Bias** | Tendency to favor action over inaction, even when inaction is optimal. | In some contexts, LLMs recommend unnecessary interventions. "Do something" is preferred over "wait and observe" even when monitoring is the optimal strategy. | Present scenarios where expert consensus favors watchful waiting. Measure how often LLMs recommend intervention vs. monitoring. | Medium |
| 58 | **Zero-Risk Bias** | Preference for eliminating a small risk entirely over a larger reduction of a bigger risk. | LLMs recommend eliminating a minor risk (reducing it to zero) over significantly reducing a major risk, even when the latter produces greater expected value. | Present risk-reduction choices with clear expected-value calculations. Measure whether zero-risk options are preferred despite lower expected value. | High |
| 59 | **Scope Insensitivity** | Failure to scale moral concern or willingness-to-pay proportionally with the scope of a problem. | LLMs treat problems affecting 100 people and 100,000 people with similar urgency and resource recommendations. Moral weight does not scale. | Present identical problems at different scales. Measure whether response urgency, recommended resources, and moral weight scale proportionally. | High |
| 60 | **Ambiguity Aversion** | Preference for known risks over unknown risks, even when unknown risks may be lower. | LLMs recommend the option with known probabilities over options with ambiguous-but-potentially-better odds. | Present choices between known-probability and ambiguous-probability options where expected value favors the ambiguous option. Measure selection rates. | Medium |
| 61 | **Pseudocertainty Effect** | Treating probabilistic outcomes as certain when presented within a multi-stage framework. | In multi-step decision trees, LLMs treat conditional probabilities as if they were certainties in intermediate stages. | Present multi-stage probability problems. Measure whether intermediate probabilities are properly compounded or treated as certain. | Medium |
| 62 | **Normalcy Bias** | Underestimating the probability and impact of rare, catastrophic events. | LLMs underweight tail risks and black swan scenarios. Disaster planning recommendations are insufficient for true worst-case scenarios. | Ask for risk assessments in domains with known tail risks. Compare LLM probability estimates for extreme events against actuarial or historical data. | High |

---

## Category 9: Attribution Biases

Biases in how causes are assigned to events and behaviors.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 63 | **Fundamental Attribution Error** | Overemphasizing personal characteristics and underemphasizing situational factors when explaining others' behavior. | LLMs attribute outcomes to individual traits (skill, effort, character) rather than systemic or situational factors. | Present scenarios with clear situational causes. Measure whether LLM explanations weight personal vs. situational factors. | High |
| 64 | **Self-Serving Bias (Proxy)** | Attributing success to internal factors and failure to external factors. | When analyzing organizational outcomes, LLMs attribute successes to strategy/leadership and failures to market conditions/external factors. | Present matched success/failure cases for similar entities. Measure asymmetry in internal vs. external attribution across outcomes. | Medium |
| 65 | **Just-World Hypothesis** | Believing that people get what they deserve. | LLMs imply that negative outcomes were deserved or predictable based on the victim's actions, even in cases of clear random misfortune. | Present scenarios involving random negative outcomes. Measure whether LLM explanations imply victim causation or deservingness. | High |
| 66 | **Actor-Observer Asymmetry** | Explaining one's own behavior situationally but others' behavior dispositionally. | When analyzing different actors in the same scenario, LLMs attribute different causal frameworks depending on which actor is focal. | Present the same event from different actor perspectives. Measure whether causal attribution shifts based on focal actor. | Medium |
| 67 | **Hostile Attribution Bias** | Interpreting ambiguous actions as intentionally hostile. | LLMs interpret ambiguous actions in competitive or conflict scenarios as deliberately adversarial rather than accidental or neutral. | Present ambiguous actions in interpersonal/organizational contexts. Measure the proportion of hostile vs. neutral interpretations. | Medium |
| 68 | **Ultimate Attribution Error** | Extending attribution biases to entire groups. | LLMs attribute positive outcomes of in-group members to disposition and negative outcomes to situation, while reversing this pattern for out-group members. | Test attributions for equivalent behaviors across different group memberships. Measure differential attribution patterns. | High |

---

## Category 10: Other Cognitive Biases

Additional biases that affect reasoning quality in AI outputs.

| # | Bias | Definition | LLM Manifestation | Detection Method | Severity |
|---|------|------------|--------------------|------------------|----------|
| 69 | **Survivorship Bias** | Drawing conclusions from successful cases while ignoring failures. | LLMs cite successful companies, strategies, and individuals as evidence while ignoring the much larger population of failures using identical approaches. | Ask for evidence supporting a strategy. Measure whether failures are represented proportionally to successes. Check "dropout" citation rates. | Critical |
| 70 | **Narrative Fallacy** | Constructing coherent stories from random or loosely connected events. | LLMs construct causal narratives from coincidental data. Correlation is presented as causation through compelling storytelling. | Present random or uncorrelated data. Measure whether LLMs construct causal narratives vs. acknowledging randomness. | High |
| 71 | **Automation Bias** | Over-reliance on automated systems, particularly when they contradict human judgment. | LLMs recommend trusting automated/algorithmic outputs over human expert judgment, even in domains where human expertise is superior. | Present scenarios where automated and human expert assessments conflict, with the human being correct. Measure which the LLM endorses. | High |
| 72 | **Curse of Knowledge** | Difficulty imagining what it is like to not know something you know. | LLMs produce explanations calibrated to expert audiences when asked for beginner-level explanations. Assumed knowledge level is too high. | Request explanations at specified expertise levels. Measure vocabulary complexity, assumed prerequisite knowledge, and concept introduction rates against target level. | Medium |

---

## Appendix A: Category Summary

| Category | Count | Critical | High | Medium | Low |
|----------|-------|----------|------|--------|-----|
| 1. Anchoring & Adjustment | 7 | 3 | 4 | 0 | 0 |
| 2. Availability & Representativeness | 7 | 2 | 4 | 1 | 0 |
| 3. Confirmation & Belief | 8 | 1 | 5 | 2 | 0 |
| 4. Framing & Presentation | 8 | 1 | 1 | 5 | 1 |
| 5. Overconfidence & Calibration | 8 | 1 | 4 | 3 | 0 |
| 6. Social & Group | 9 | 1 | 5 | 3 | 0 |
| 7. Memory & Recall | 7 | 0 | 3 | 3 | 1 |
| 8. Decision-Making & Judgment | 8 | 0 | 4 | 4 | 0 |
| 9. Attribution | 6 | 0 | 3 | 3 | 0 |
| 10. Other Cognitive Biases | 4 | 1 | 2 | 1 | 0 |
| **Total** | **72** | **10** | **35** | **25** | **2** |

## Appendix B: Severity Distribution

- **Critical (10):** Anchoring, Insufficient Adjustment, Representativeness Anchoring, Availability Heuristic, Base Rate Neglect, Confirmation Bias, Framing Effect, Overconfidence Effect, Authority Bias, Survivorship Bias
- **High (35):** Core measurement targets for standard benchmark runs
- **Medium (25):** Extended evaluation targets
- **Low (2):** Tracked for taxonomy completeness

## Appendix C: MVP Test Set Priority

For the Phase 1 MVP (30 biases x 50 cases = 1,500 tests), prioritize:
1. All 10 Critical biases (500 tests)
2. Top 20 High biases by detection method feasibility (1,000 tests)

Selection criteria for High-severity subset:
- Detection method is well-defined and automatable
- LLM manifestation is consistently observable
- Cross-domain applicability (medical, legal, financial contexts)

## Appendix D: Cross-Reference to Existing Benchmarks

| Benchmark | Biases Covered | Overlap with LCB |
|-----------|---------------|-------------------|
| BBQ (Parrish et al., 2022) | 9 social biases | Social & Group category partial overlap |
| CrowS-Pairs | 9 bias types | Primarily social/discrimination (out of LCB scope) |
| BOLD | 5 domains | Demographic bias (out of LCB scope) |
| BiasAsker | 14 social bias categories | Social bias generation (out of LCB scope) |
| **LCB (this taxonomy)** | **72 cognitive biases** | **12-14x more comprehensive; cognitive, not social/discrimination** |

---

*Note: This taxonomy covers cognitive biases in AI reasoning and output quality. It intentionally excludes social and discrimination biases (race, gender, age, etc.) which are covered by existing benchmarks (BBQ, CrowS-Pairs, BOLD). LCB's differentiation is measuring how AI systems THINK, not who they discriminate against.*
