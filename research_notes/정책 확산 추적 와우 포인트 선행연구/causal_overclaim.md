# Causal overclaiming and evidence-strength calibration in (retrieval-augmented) text generation: prior work for the "evidence-level-conditioned diffusion narrative" wow point

Verification legend used throughout:
- **[V]** = bibliographic details (authors, title, venue, year) checked on the official page during this session (ACL Anthology, PMLR, ICLR proceedings, arXiv abs page, KCI, PMC, publisher page).
- **[V-PDF]** = also read the relevant sections of the paper PDF (labels, agreement, numbers).
- **[P]** = partially verified: confirmed through a search-result listing of the official page, or through a secondary source, but the primary page was not opened or some details could not be seen.
- **[U]** = not verified in this session. Do not cite without checking.

Process note: the session's web-search budget ran out near the end. A few planned checks could not be run; they are listed under the Gaps headings. Direct page fetches still worked and were used for the last verifications.

---

## Q1. Has anyone conditioned RAG or grounded generation on evidence strength or evidence type to prevent causal overclaiming? What is the closest work?

### Takeaway
I found no work that does exactly what we propose. Our design gives each **inter-document link** a typed evidence level (explicit reference / common external factor / temporal order only / order unknown). It caps the causal or certainty strength of the generated wording at that level, and it measures a causal-overclaim rate. The closest prior work is **Fan et al. (arXiv, Aug 2026), "Claim-locked reporting"**. Before the LLM writes, that system fixes each claim's evidence source, numbers, direction and *allowed language strength*. It does this for statistical reports (fMRI, RCTs), though, and has no causal-versus-temporal relation typology. Other neighbours treat evidence as graded *support or sufficiency* and control answer-or-abstain, not graded causal wording. These are Self-RAG ISSUP, the Evidence Sufficiency Benchmark and Trust-Align. A separate line calibrates wording to the model's *internal* confidence rather than to external evidence type: Mielke 2022, Band 2024, Yona 2024 and Liu 2026 (see Q4).

### Cited Findings
- **Fan, X., Li, J., Guo, H., Han, Y., Zhang, Y. (2026). "Provenance Before Prose: Claim-Locked Reporting for Statistical Text Generation." arXiv:2608.25336 (v1 26 Aug 2026, v2 19 Sep 2026; no venue listed). [V]**
  - **What they did:** They frame report generation as a control problem. Before the LLM writes connective prose, "claim-locked reporting" fixes each reportable claim's evidence source, numbers, direction and allowed language strength. They evaluated it on fMRI functional-connectivity reporting and on RCT reporting (Evidence Inference 2.0). It improves cross-seed reproducibility over a deterministic hybrid template by 37.4 and 20.5 points. The hybrid template reproduces only 61.1% of report-visible numbers. Blinded human audits support the direction-preservation findings. — [arXiv abs](https://arxiv.org/abs/2608.25336)
  - **Relation:** This is the **main novelty threat and a method to adopt.** It makes the same core move we do: a strength ceiling fixed upstream of the LLM, with the LLM limited to connective prose. Our points of difference:
    - Our ceiling comes from a *typed relation-evidence level between documents* (causal vs. common driver vs. temporal-only), not from statistical results.
    - The target is cross-council propagation narratives in Korean minutes.
    - We add an explicit overclaim-rate metric and an abstention path.
  - A secondary search summary claimed the paper has a "strong-language rate" column on which the hybrid template is not best. This is not in the abstract and is unverified.
- **Asai, A., Wu, Z., Wang, Y., Sil, A., Hajishirzi, H. (2024). "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection." ICLR 2024. [V]** — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/25f7be9694d7b32d5cc670927b8091e1-Abstract-Conference.html); [arXiv:2310.11511](https://arxiv.org/pdf/2310.11511)
  - **What they did:** They trained a single LM to emit reflection tokens (Retrieve, IsRel, IsSup, IsUse), which allow controllable, critique-guided inference. At 7B and 13B it beats ChatGPT and retrieval-augmented Llama2-chat on open-domain QA, reasoning and fact verification, and it improves citation accuracy in long-form generation. — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2024/hash/25f7be9694d7b32d5cc670927b8091e1-Abstract-Conference.html)
  - ISSUP is graded *fully supported / partially supported / no support or contradictory*. [P: wording from the paper text via search snippet] — [arXiv PDF](https://arxiv.org/pdf/2310.11511)
  - **Relation:** A method to adopt (critic labels plus critique-guided regeneration) and a point of differentiation. ISSUP scores *entailment support*, not whether the *type* of evidence licenses causal wording.
- **Song, M., Sim, S. H., Bhardwaj, R., Chieu, H. L., Majumder, N., Poria, S. (2025). "Measuring and Enhancing Trustworthiness of LLMs in RAG through Grounded Attributions and Learning to Refuse." ICLR 2025 (oral). [P: confirmed through ICLR proceedings and arXiv listings in search results]** — [ICLR proceedings](https://proceedings.iclr.cc/paper_files/paper/2025/hash/4c88827decab6c046b881a2c3a99c76f-Abstract-Conference.html); [arXiv:2409.11242](https://arxiv.org/abs/2409.11242v3)
  - **What they did:** They introduce Trust-Score, which covers grounded refusals, answer correctness and citation recall/precision. They also introduce Trust-Align, a DPO method on a constructed dataset, tested on LLaMA (1–8B), **Qwen-2.5 (0.5–7B)** and Phi-3.5. 26 of 27 aligned models beat baselines on ASQA, QAMPARI and ELI5. Prompting methods such as in-context learning fail to adapt LLMs well to RAG as measured by Trust-Score. Code: github.com/declare-lab/trust-align.
  - **Relation:** Metrics and method to adopt: refusal plus citation precision/recall, and DPO on small open models including Qwen2.5-7B. Point of difference: refusal is binary on answerability, with no graded claim strength.
- **Zhang, H., Wu, W. (2026). "Do LLMs Know When Evidence is Insufficient? An Evidence Sufficiency Benchmark for Answer-Abstention Calibration in Retrieval-Augmented Generation." *Computers, Materials & Continua* 89(1), Article 69. DOI 10.32604/cmc.2026.086343. [V]** — [Tech Science Press](https://www.techscience.com/cmc/v89n1/68467)
  - **What they did:** They built a five-level evidence gradient, from L1 (full support) to L5 (conflicting evidence); the abstract lists fully supportive, partially supportive, irrelevant, absent and conflicting. They tested 7 LLMs from 5 families under 3 prompting strategies.
  - Results: under conflicting evidence, over-answer rates were 65–91%. Answer rates fall as evidence weakens, but abstention stays unreliable. Chain-of-thought helps inconsistently. Automatic evaluation was validated on 200 human-checked samples.
  - **Relation:** This is the closest work in spirit ("graded evidence level → model behaviour"), but its output is answer-or-abstain, not graded linguistic strength. It supports our abstention branch, and it shows LLMs do not reliably self-abstain, so an external checker is justified.
- **Arasteh, S. T. (2026). "The strength of clinical evidence is recoverable from language model representations but not from their stated grades." arXiv:2606.29034 (single author, preprint). [V]** — [arXiv abs](https://arxiv.org/abs/2606.29034)
  - **What they did:** They used 45,134 clinical claims, of which 20,611 were harmonized into a 4-level evidence grade under 3 frameworks, and 22 open-weight LLMs (0.6–70B). A linear probe recovers the grade (median AUROC 71.8), but grades the models *state* are at chance, 25–27 points below the probe.
  - **Relation:** This is evidence *against* letting the 7B model self-assign the evidence level. We assign the level deterministically from dates and explicit-reference string evidence, which is both a design justification and a point of difference.
- **Liu, G. K.-M., Caciularu, A., Yona, G., Szpektor, I., Cohan, A. (2026). "Reinforcement Learning with Metacognitive Feedback Elicits Faithful Uncertainty Expression in LLMs." arXiv:2606.32032. [V]** — [arXiv abs](https://arxiv.org/abs/2606.32032)
  - **What they did:** A two-stage method. First, calibrate numeric self-confidence with RLMF (up to 63% better than standard RL). Then map confidence to natural-language uncertainty through targeted output editing.
  - **Relation:** Their "confidence → hedge phrase" mapping parallels our "evidence level → allowed phrase" mapping, but the driver is *internal confidence*, not external evidence type. Point of differentiation.
- **Santesso, N., Glenton, C., Dahm, P., Garner, P., Akl, E., Alper, B., Brignardello-Petersen, R., Carrasco-Labra, A., De Beer, H., Hultcrantz, M., Kuijpers, T., Meerpohl, J., Morgan, R., Mustafa, R., Skoetz, N., Sultan, S., Wiysonge, C., Guyatt, G., Schünemann, H. J. "GRADE guidelines 26: Informative statements to communicate the findings of systematic reviews of interventions." *Journal of Clinical Epidemiology* (online 9 Nov 2019; 2020 issue). DOI 10.1016/j.jclinepi.2019.10.014. [P: citation verified on the GRADE Working Group blog; journal page returned 403]** — [GRADE blog](https://usblog.gradeworkinggroup.org/2020/02/research-shorts-informative-statements.html); [McMaster record](https://experts.mcmaster.ca/display/publication1676921)
  - **What they did:** Standardized statements that combine effect size with *certainty of evidence*, developed through workshops (80 attendees) and a survey (110 producers and users of systematic reviews). Statements for low, moderate and high certainty were acceptable to more than 60% of respondents. The table is organized by certainty and then by effect size. — [search summary of abstract](https://scholarworks.aub.edu.lb/items/150f8336-18df-4e43-9c2e-5d8e7788217b)
  - Secondary summaries give the verb ladder as "results in" (high), "likely results in" (moderate), "may result in" (low) and "the evidence is very uncertain" (very low). **[U: the exact table wording was not seen on the primary source.]**
  - **Relation:** A method to adopt and a strong framing anchor. It is a human-validated, institutionalized precedent for an "evidence level → mandated wording" table, which is the human-practice analogue of our level-conditioned phrase whitelist.
- **Gao, L., Dai, Z., Pasupat, P., Chen, A., Chaganty, A. T., Fan, Y., Zhao, V., Lao, N., Lee, H., Juan, D.-C., Guu, K. (2023). "RARR: Researching and Revising What Language Models Say, Using Language Models." ACL 2023, pp. 16477–16508. [V]** — [ACL Anthology](https://aclanthology.org/2023.acl-long.910/)
  - **What they did:** Post-hoc attribution. The system researches evidence and edits unsupported statements while preserving the rest of the text.
  - **Relation:** A method to adopt for a "check → minimally revise" loop. It does not target claim strength.
- **Dhuliawala, S., Komeili, M., Xu, J., Raileanu, R., Li, X., Celikyilmaz, A., Weston, J. (2024). "Chain-of-Verification Reduces Hallucination in Large Language Models." Findings of ACL 2024, pp. 3563–3578. [V]** — [ACL Anthology](https://aclanthology.org/2024.findings-acl.212/)
  - **What they did:** The model drafts an answer, writes verification questions, answers them independently, and then revises its response.
  - **Relation:** A method to adopt for the regeneration loop, with strength-specific verification questions such as "Does the evidence contain an explicit mention of council A?"
- **Wen, B., Yao, J., Feng, S., Xu, C., Tsvetkov, Y., Howe, B., Wang, L. L. "Know Your Limits: A Survey of Abstention in Large Language Models." arXiv:2407.18418 (v3 12 Feb 2025; arXiv comment says TACL). [V for arXiv; TACL volume and pages not verified]** — [arXiv abs](https://arxiv.org/abs/2407.18418)
  - **Relation:** A framing reference for treating abstention as a first-class output.

### Inferences
- The individual ingredients all exist: strength-capped generation (Fan 2026; GRADE 26), support critics (Self-RAG), graded-evidence abstention (ESB) and verify-and-revise loops (RARR, CoVe). The new element is the **evidence *type* axis for links between documents**, together with **causal language as the controlled variable**. Our claim should be framed as "to our knowledge, first to type inter-document *diffusion* evidence and calibrate causal and certainty language to it, with a measured overclaim rate". It should not be framed as "first to constrain claim strength".
- The competition rule (no causal assertions between councils; only temporal order and explicit cross-references) is a hard ceiling that sits *below* "causal" for every level. Our evidence ladder can therefore be framed as **compliance-by-construction**: each level licenses a specific non-causal vocabulary (temporal, attributed reference, co-mention of a shared external factor), and the overclaim rate is a measurable audit of rule compliance.
- Arasteh (2026) and ESB (2026) together suggest the evidence level should be computed outside the LLM, from rules and metadata, not elicited from it.

### Gaps
- Fan et al. (2026) was read only at abstract level. Unknown: whether it defines a strength ladder, how "allowed language strength" is operationalized, and whether it reports a strong-language rate.
- These searches were planned but not run because the search budget ran out:
  - ALCE and other citation-generation benchmarks;
  - "relation-type-aware" attributed generation;
  - policy-diffusion NLP work (bill text reuse) that might already discuss causal-language control;
  - hedge-generation papers, e.g., work on generating hedges in dialogue [U].
- A 2025–2026 paper combining RAG with causal-language control could exist that I did not find.

---

## Q2. What work detects causal vs. correlational vs. temporal-only claims in text? Datasets, labels, accuracy, licenses?

### Takeaway
A mature line of work, from Sumner et al. 2014 through Yu et al. 2019/2020 to Wright & Augenstein 2021, defines a 4–7-point **ordinal claim-strength scale**. It operationalizes **exaggeration as strength(derived text) > strength(source)**, which is exactly the shape our overclaim rate needs. Agreement on these labels is very high (κ = 0.95–0.98), and BioBERT classifiers reach about 0.87–0.88 macro-F1. All resources are English (biomedical papers or press releases). None covers Korean or legislative text, and **none has a "temporal-order-only" level**. For that we need event-relation work (Causal News Corpus, MAVEN-ERE) and the post hoc fallacy findings.

### Cited Findings
- **Yu, B., Li, Y., Wang, J. (2019). "Detecting Causal Language Use in Science Findings." EMNLP-IJCNLP 2019, pp. 4664–4674, Hong Kong. DOI 10.18653/v1/D19-1473. [V-PDF]** — [ACL Anthology](https://aclanthology.org/D19-1473/)
  - **Labels (Table 1):**
    - correlational: cues "association, associated with, predictor, at high risk of"
    - conditional causal: a causal cue plus a doubt cue ("may, might, appear to, probably")
    - direct causal: "increase, decrease, lead to, effective in, contribute to, reduce"
    - no relationship: also used for limitation statements — [PDF](https://aclanthology.org/D19-1473.pdf)
  - **Data:** 3,126 annotated PubMed conclusion sentences, of which 3,061 single-type sentences were used: correlational 998 (32.6%), conditional causal 213 (7.0%), direct causal 494 (16.1%), no relationship 1,356 (44.3%). — [PDF](https://aclanthology.org/D19-1473.pdf)
  - **Agreement:** two annotators on 30 abstracts, Cohen's κ = 0.98. — [PDF](https://aclanthology.org/D19-1473.pdf)
  - **Accuracy:** BioBERT is best, with accuracy 0.90 and macro-F1 0.88 (5-fold CV), ahead of BERT, BiRNN and LinearSVM. Conditional causal is the weakest class. — [PDF](https://aclanthology.org/D19-1473.pdf)
  - **Finding:** across about 38K observational studies, 21.7% used direct causal language exclusively in their conclusions and 32.4% used some. — [ACL Anthology](https://aclanthology.org/D19-1473/)
  - **Release and license:** corpus and code at github.com/junwang4/causal-language-use-in-science. The repo sidebar and README list **GPL-3.0**; no separate data terms are stated. — [GitHub](https://github.com/junwang4/causal-language-use-in-science). A Hugging Face mirror describes itself as this dataset (`medalpaca/medical_meadow_pubmed_causal`). [P] — [HF](https://huggingface.co/datasets/medalpaca/medical_meadow_pubmed_causal)
  - **Relation:** A method to adopt: the label scheme, the κ protocol and the cue lexicon to translate. Their "conditional causal" class (hedged causal) maps to our forbidden "hedged influence" class.
- **Yu, B., Wang, J., Guo, L., Li, Y. (2020). "Measuring Correlation-to-Causation Exaggeration in Press Releases." COLING 2020, pp. 4860–4872. DOI 10.18653/v1/2020.coling-main.427. [V-PDF]** — [ACL Anthology](https://aclanthology.org/2020.coling-main.427)
  - **Labels and agreement:** four claim types (not claim / correlational / conditional causal / direct causal). 700 press releases yield 2,076 single-type sentences. Cohen's κ = 0.95 on 200 sentences. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
  - **Classifier:** BioBERT macro-F1 0.868, or 0.892 with data augmentation. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
  - **Exaggeration rule (conservative, pre-declared):**
    - the paper's conclusion counts as correlational if it has correlational sentences and no causal ones;
    - the press release is exaggerated if its headline is predicted *direct causal*, or, when the headline is "not claim", if the first and second sentences are predicted direct causal (both, or one with the other "not claim");
    - *conditional causal from correlational is deliberately not counted*. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
  - **Result:** 1,391 of 6,244 cases (22%) exaggerated. University press releases exaggerated more than journal releases. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
  - **Mapping to the seven-point Sumner et al. (2014) scale:** no statement / explicit no relation / correlational / ambiguous ("linked to") / conditional causal ("may", "might") / "can" causal / unconditionally causal. Sumner found 33% exaggeration in 462 UK university press releases. Adams et al. (2017) re-analysed on a 5-point scale and got 19%. [P: both reported inside Yu 2020; originals not opened] — [PDF](https://aclanthology.org/2020.coling-main.427.pdf); replication context in [Bratton et al., PMC](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6833989/)
  - **License:** the paper is under CC BY 4.0. Code and data are at github.com/junwang4/correlation-to-causation-exaggeration, and **no license is visible on the repo page**. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf); [GitHub](https://github.com/junwang4/correlation-to-causation-exaggeration)
  - **Relation:** **The most direct methodological template for a "causal overclaim rate"**: overclaim = strength(generated) > strength(licensed by source). It also shows the value of a conservative, pre-declared aggregation rule and of separating hedged-causal from direct-causal.
- **Wright, D., Augenstein, I. (2021). "Semi-Supervised Exaggeration Detection of Health Science Press Releases." EMNLP 2021, pp. 10824–10836. DOI 10.18653/v1/2021.emnlp-main.845. [V]** — [ACL Anthology](https://aclanthology.org/2021.emnlp-main.845); [arXiv:2108.13493](https://arxiv.org/abs/2108.13493)
  - **What they did:** They formalize exaggeration detection and build a benchmark of press-release/abstract pairs from earlier expert-annotated studies. MT-PET (multi-task Pattern-Exploiting Training with cloze-style auxiliary tasks) beats PET and supervised learning in both low- and high-resource settings. — [ACL Anthology](https://aclanthology.org/2021.emnlp-main.845)
  - The benchmark has 563 expert-annotated tuples, and the task is split into (1) claim strength and (2) exaggeration level. [P: NVIDIA blog] — [NVIDIA blog](https://blogs.nvidia.com/blog/exaggeration-detector/)
  - Direct causal claims are the hardest category. [P: arXiv text via search snippet] — [arXiv PDF](https://arxiv.org/pdf/2108.13493)
  - The ACL page lists no code or data link.
  - **Relation:** A method to adopt. PET- or cloze-style few-shot training suits our situation, where we will have only a few hundred Korean labels. Their two-step formulation (strength of each text, then compare) mirrors ours: evidence level, then statement strength.
- **Pei, J., Jurgens, D. (2021). "Measuring Sentence-Level and Aspect-Level (Un)certainty in Science Communications." EMNLP 2021, pp. 9959–10011. DOI 10.18653/v1/2021.emnlp-main.784. [P]** — [ACL Anthology](https://aclanthology.org/2021.emnlp-main.784); [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10336737)
  - **What they did:** They annotated 2,167 scientific findings. Hedge words explain only part of perceived certainty. Pretrained LMs predict sentence- and aspect-level certainty, and the method was applied to 431K findings. The model and data are released on the authors' project site (license not checked). — [NSF PAR PDF](https://par.nsf.gov/servlets/purl/10336737); [Papers with Code](https://astro.paperswithcode.com/paper/measuring-sentence-level-and-aspect-level-un)
  - **Relation:** A hedge lexicon alone under-measures certainty, so our detector should use a classifier, with the lexicon serving as a high-recall prefilter.
- **Haber, N. A., et al. (2022). "Causal and Associational Language in Observational Health Research: A Systematic Evaluation." *American Journal of Epidemiology* 191(12):2084–2097. DOI 10.1093/aje/kwac137. [P: confirmed through institutional repository listings]** — [eScholarship](https://escholarship.org/uc/item/5c56c6gk); [St Andrews repository](https://research-repository.st-andrews.ac.uk/handle/10023/28097)
  - **What they did:** Three reviewers rated implied causality in 1,170 articles from 18 journals.
  - Abstract linking language was rated none 13.8%, weak 34.2%, moderate 33.2% and strong 18.7%. "Associate" was the most common root (45.7%). Ratings of word roots were *highly heterogeneous*, and over half of reviewers rated "association" as having some causal implication.
  - Action recommendations implied more causality than the linking sentence in 44.5% of articles and the same amount in 40.3%.
  - **Relation:** Perceived strength of individual words is inconsistent, so we need a written ladder with examples and measured agreement. **Action-guiding sentences need separate scrutiny**, which is relevant to the J2 forecast text.
- **Tan, F. A., Hürriyetoğlu, A., Caselli, T., Oostdijk, N., Nomoto, T., Hettiarachchi, H., Ameer, I., Uca, O., Liza, F. F., Hu, T. (2022). "The Causal News Corpus: Annotating Causal Relations in Event Sentences from News." LREC 2022, pp. 2298–2310. [V]** — [ACL Anthology](https://aclanthology.org/2022.lrec-1.246/)
  - **What they did:** 3,559 protest-news event sentences labeled causal or non-causal. A PLM baseline reaches 81.20% F1 on test and 83.46% in 5-fold CV. Trained on CausalTimeBank and PDTB and tested here without fine-tuning, it drops to about 64% F1. Crowd annotation is hard for non-experts. The page states no corpus license (the paper itself is CC BY 4.0 under the Anthology footer).
  - **Relation:** News and politics is closer to our domain than PubMed. The cross-corpus drop warns that we should expect domain shift to Korean minutes and need in-domain labels.
- **Joshi, N., Saparov, A., Wang, Y., He, H. (2024). "LLMs Are Prone to Fallacies in Causal Inference." EMNLP 2024, pp. 10553–10569. [V]** — [ACL Anthology](https://aclanthology.org/2024.emnlp-main.590)
  - **What they did:** They fine-tuned LLMs on synthetic data with temporal, spatial and counterfactual relations. Models use the order in which events are *mentioned* as a causal cue, and they commit the **post hoc fallacy** ("X before Y" ⇒ "X causes Y") even when order is randomized. They can, however, infer the *absence* of causation from temporal or spatial relations.
  - **Relation:** **Key motivation.** Our data is exactly "Council A discussed issue X before Council B". LLMs are predisposed to turn precedence into influence (e.g., "A시의회의 영향을 받아 B도의회가…"). The "temporal-order-only" level targets this documented failure.
- **Jin, Z., et al. (2024). "Can Large Language Models Infer Causation from Correlation?" ICLR 2024. arXiv:2306.05836. [P]** — [arXiv](https://arxiv.org/pdf/2306.05836); [ICLR poster](https://iclr.cc/virtual/2024/poster/17518)
  - **What they did:** The Corr2Cause benchmark (over 200K samples in v2). Seventeen LLMs score near chance, and fine-tuned models fail under perturbation.
  - **Relation:** Background showing that LLM causal judgments are unreliable, so the decision about causality should not be delegated to the LLM.
- **Farkas, R., Vincze, V., Móra, G., Csirik, J., Szarvas, G. (2010). "The CoNLL-2010 Shared Task: Learning to Detect Hedges and their Scope in Natural Language Text." Proceedings of CoNLL-2010 Shared Task, pp. 1–12, Uppsala. [V]** — [ACL Anthology](https://aclanthology.org/W10-3001/)
  - **What they did:** Task 1 is sentence-level certain vs. uncertain classification (BioScope biomedical texts plus Wikipedia "weasel" annotations). Task 2 is in-sentence hedge-cue scope.
  - **Relation:** The foundational evaluation design: sentence-level F1 on the uncertain class plus cue/scope F1.
- **MAVEN-ERE (Wang et al.), arXiv:2211.07342.** It annotates temporal and causal relations jointly and defines causal links as CAUSE vs. PRECONDITION. [P: definition seen in a search snippet; venue (EMNLP 2022) not verified] — [arXiv PDF](https://arxiv.org/pdf/2211.07342)
  - **Relation:** A guideline source for keeping temporal and causal relations between events separate.

### Inferences
- **Our ladder = Yu's 4 classes + two link-specific classes.** We need classes Yu does not have:
  - "temporal-only" ("이후", "뒤이어");
  - "attributed explicit reference" ("B의회 회의록에서 A시 사례를 언급") — a reporting class, not a causal one.

  The Sumner 7-point scale shows that finer ordinal scales are annotatable. Sumner, Adams and Yu all show, though, that what you count as "exaggeration" changes the headline rate (33% vs. 19% vs. 22%). **The aggregation rule must be pre-declared.**
- **Licensing:** the English resources are usable at most as a source of label schemes, cue lexicons and perhaps translated augmentation.
  - The Yu 2019 repo is GPL-3.0.
  - The Yu 2020 repo states no license.
  - The Causal News Corpus states no corpus license on the Anthology page.

  For the competition we need the *scheme*, not the data. Check the competition rules on external training data before using any of it.

### Gaps
- No Korean causal-strength dataset was found (see Q5).
- Wright & Augenstein's per-class scores and data release URL were not checked (the ACL page lists none; a "copenlu" GitHub repo is likely but **[U]**).
- The original Sumner et al. 2014 (BMJ) and Adams et al. 2017 papers were not opened; their figures are cited through Yu 2020.
- I could not search for causal-claim detection specifically in parliamentary or legislative text.

---

## Q3. What work shows LLMs overgeneralize or exaggerate claims in summaries (2023–2026)?

### Takeaway
Strong, recent and partly peer-reviewed evidence shows that LLM summaries inflate scope and causal strength:
- Peters & Chin-Yee 2025, *Royal Society Open Science*;
- Isch et al. 2026, *Nature Human Behaviour*: LLM summaries strip hedges and add causal claims;
- Carro et al. 2024: correlational findings become causal headlines;
- Yun et al. 2025: spin carries into LLM summaries.

Asking for "accuracy" can **backfire**, while temperature 0 and explicit caution or self-audit prompts help. Causal caution collapses in "practical advice" contexts, which is the register of the competition's diffusion-forecast section.

### Cited Findings
- **Peters, U., Chin-Yee, B. (2025). "Generalization bias in large language model summarization of scientific research." *Royal Society Open Science* 12(4):241776. DOI 10.1098/rsos.241776 (published 30 Apr 2025). [V]** — [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/); [arXiv:2504.00025](https://arxiv.org/abs/2504.00025v1)
  - **Design:** 10 LLMs (GPT-3.5/4 Turbo, ChatGPT-4o, ChatGPT-4.5, LLaMA 2 70B, LLaMA 3.3 70B, Claude 2/3.5/3.7, DeepSeek) produced 4,900 summaries.
  - **Coding:** each summary was coded "generalized" or "restricted" using three markers: *generics*, *present tense* for past findings, and *action-guiding* recommendations. Two expert coders plus a blinded third coder on 100 texts gave **κ = 0.79–0.95**.
  - **Results:**
    - LLM summaries were about twice as likely as the originals to contain generalized conclusions, and 6 of the 10 models overgeneralized significantly.
    - Newer models were worse: LLaMA 3.3 70B had about 39× the odds and ChatGPT-4o about 9×.
    - **An accuracy-focused prompt raised the odds (OR 1.90, 95% CI 1.11–3.26).**
    - **Temperature 0 made generalized conclusions 76% less likely than temperature 0.7.**
    - LLM summaries were more generalized than NEJM Journal Watch expert summaries (OR 4.85, 95% CI 3.06–7.70).
  - **Relation:** A coding scheme and κ protocol to adopt. Practical rules: greedy or temperature-0 decoding, and avoid "be accurate" instructions. The present-tense and action-guiding markers also apply to Korean narrative and forecast text.
- **Isch, C., Dörr, T., Fasching, N., Jennings, G., Watts, D. J. (2026). "Quantifying the prevalence and impact of overreaching causal claims in social science." *Nature Human Behaviour* (article s41562-026-02553-x; August 2026). [P: the Nature page redirected to login; authors from a Marginal Revolution post dated 26 Aug 2026, other details from search-result coverage]** — [Nature](https://www.nature.com/articles/s41562-026-02553-x); [Marginal Revolution](https://marginalrevolution.com/marginalrevolution/2026/08/overreaching-causal-language-in-the-social-sciences.html)
  - **Prevalence:** LLMs were used to classify 194,631 cross-sectional articles (1980–2024). About 46% used causal language in their titles or abstracts, rising from about 20% (2000) to about 60% (2024). A claim-level match of full text to abstract on 100 articles found 26.8% causal overreach. — [Marginal Revolution](https://marginalrevolution.com/marginalrevolution/2026/08/overreaching-causal-language-in-the-social-sciences.html); [coverage](https://siliconcanals.com/s-researchers-rewrote-study-abstracts-to-strip-out-the-causal-wording-and-about-half-the-readers-still-described-the-findings-as-one-thing-causing-another-with-the-wording-left-in-and-a-note-attached/)
  - **Reader experiment (N = 1,105):** methodological labels (β = −0.4) and associational wording (β = −0.3) reduced causal readings, but participants often reintroduced causal phrasing in their own summaries.
  - **LLM experiment:** "model summaries of these articles (N = 100 each) can amplify causal overstatement, removing hedges and introducing causal claims where articles used strictly associational phrasing; however, prompting caution diminishes this pattern" (five LLMs). — [coverage](https://siliconcanals.com/s-researchers-rewrote-study-abstracts-to-strip-out-the-causal-wording-and-about-half-the-readers-still-described-the-findings-as-one-thing-causing-another-with-the-wording-left-in-and-a-note-attached/)
  - **Relation:** The newest and highest-profile evidence. LLM-scale classification of causal language passed review at a top venue (validation details not seen), and LLM summaries *remove hedges*, which is exactly the failure our checker targets.
- **Carro, M. V., Gauna Selasco, F., Mester, D. A., Leiva, M. A. (2024). "Are UFOs Driving Innovation? The Illusion of Causality in Large Language Models." arXiv:2410.11684. [V]** — [arXiv abs](https://arxiv.org/abs/2410.11684)
  - **What they did:** GPT-4o-Mini, Claude-3.5-Sonnet and Gemini-1.5-Pro wrote news headlines from correlational abstracts, and the authors measured causal illusion. **Sycophantic prompts, where the user states a causal belief, increased causal framing**, most for GPT-4o-Mini; Claude-3.5-Sonnet was the most robust.
  - **Relation:** This is causal exaggeration at *generation* time. Our prompts and query templates should not presuppose causation. For example, use "어떤 순서로 논의되었는가" (in what order was it discussed) rather than "어떻게 확산되었는가" (how did it spread).
- **Yun, H. S., Zhang, K. Y. C., Kouzy, R., Marshall, I. J., Li, J. J., Wallace, B. C. (2025). "Caught in the Web of Words: Do LLMs Fall for Spin in Medical Literature?" Proceedings of CHIL 2025, PMLR 287. arXiv:2502.07963. [P: PMLR and arXiv listings seen in search results]** — [PMLR](https://proceedings.mlr.press/v287/yun25a.html); [arXiv](https://arxiv.org/abs/2502.07963)
  - **What they did:** All 22 LLMs tested were more susceptible to spin than clinicians. They can recognize spin when asked, prompting mitigates it, and spin propagates into the plain-language summaries they generate.
  - **Relation:** Source-text rhetoric propagates. Minutes contain speakers' own causal claims (e.g., "타 시도에서 시행해 효과를 봤다"). The checker must tell *attributed quotation* ("○○ 의원은 '…'라고 발언") apart from *system assertion*.
- **Okumura, H. (2026). "When Helpfulness Overrides Causal Caution: Context-Dependent Suppression and Recovery in LLMs." arXiv:2606.24370 (single author; also SSRN 6965680). [V]** — [arXiv abs](https://arxiv.org/abs/2606.24370)
  - **What they did:** Tested Claude Sonnet 4.6, Claude Opus 4.7, GPT 5.5 and Gemini 3.1 Pro over 480 trials.
    - "Causal caution" was maintained 91.7–100% of the time in academic contexts but only 6.7–18.3% in practical advisory contexts.
    - Only 1 of 200 practical recommendation responses kept caution.
    - **A short self-correction prompt raised maintenance to 71.4–100%.**
  - **Relation:** The J2 "future diffusion likelihood" section is an advisory-style context, so it carries high risk. This supports a separate causal self-audit pass. Caveats: a single-author preprint, frontier models only, and results not shown for 7B models.
- Joshi et al. (2024), the post hoc fallacy paper in Q2, also belongs here as a generation-relevant failure mode. — [ACL Anthology](https://aclanthology.org/2024.emnlp-main.590)

### Inferences
- These studies support a pre-registered *hypothesis* for our project: a vanilla Qwen2.5-7B RAG narrative over temporally ordered council minutes will show a non-trivial causal-overclaim rate. The supporting evidence is the post hoc fallacy, RLHF-induced assertiveness (Zhou et al. 2024, Q4) and hedge-stripping in summaries. **This must be measured, not asserted.** A small pilot (e.g., 30–50 issue narratives) would turn it into a demonstrated motivation.
- "Prompting caution" helps (Isch 2026; Okumura 2026), but "prompting accuracy" can backfire (Peters 2025). Prompts alone are therefore an unreliable control, which argues for a checker plus regeneration and a template fallback.

### Gaps
- No study found of LLM causal overclaiming in Korean, or with 7B open models in RAG.
- The Isch et al. classifier validation and the coding of the LLM-summary experiment were not seen (Nature page inaccessible).

---

## Q4. Linguistic and epistemic calibration and uncertainty expression in LLM outputs: how are these measured?

### Takeaway
The calibration literature measures alignment between *expressed* certainty (hedges, epistemic markers, decisiveness or assertiveness) and *the model's own* correctness probability or intrinsic confidence. Metrics include calibration of verbal confidence bins against accuracy, reader-forecast calibration, the gap between decisiveness and intrinsic confidence, and assertiveness regression validated on human labels. **Our target differs:** we align expressed strength with an *external evidence type*. We can reuse the methods: marker typologies, assertion-level decomposition, decisiveness scoring, control-token conditioning and reader-based evaluation.

### Cited Findings
- **Mielke, S. J., Szlam, A., Dinan, E., Boureau, Y.-L. (2022). "Reducing Conversational Agents' Overconfidence Through Linguistic Calibration." TACL 10:857–872. DOI 10.1162/tacl_a_00494. [V]** — [ACL Anthology](https://aclanthology.org/2022.tacl-1.50/); [arXiv:2012.14983](https://arxiv.org/abs/2012.14983v2)
  - **What they did:** Chit-chat models are poorly calibrated in the doubt they verbalize, yet correctness is predictable. Adding the predicted correctness as a control signal to a controllable generator greatly improves linguistic calibration.
  - **Relation:** **The architecturally closest calibration precedent.** A control token (a confidence bucket) conditions the generator, much like our evidence-level token. Difference: their control signal is predicted correctness; ours is typed external evidence.
- **Zhou, K., Jurafsky, D., Hashimoto, T. (2023). "Navigating the Grey Area: How Expressions of Uncertainty and Overconfidence Affect Language Models." EMNLP 2023, pp. 5506–5524. [V]** — [ACL Anthology](https://aclanthology.org/2023.emnlp-main.335); [arXiv:2302.13439](https://arxiv.org/abs/2302.13439v1)
  - **What they did:** They built a typology of epistemic markers and tested 50 of them in prompts. Accuracy varied by more than 80% depending on the marker. Strengtheners were about 7% worse than weakeners; factive verbs hurt and evidentials helped. Teaching models to emit certainty hurt calibration.
  - **Relation:** A source typology (weakeners / strengtheners / factives / evidentials) for building the Korean marker inventory. Korean evidentials and attributions such as "~에 따르면" and "~라고 밝혔다" are *safe* reporting forms.
- **Zhou, K., Hwang, J. D., Ren, X., Sap, M. (2024). "Relying on the Unreliable: The Impact of Language Models' Reluctance to Express Uncertainty." ACL 2024, pp. 3623–3643. [V]** — [ACL Anthology](https://aclanthology.org/2024.acl-long.198); [arXiv:2401.06730](https://arxiv.org/abs/2401.06730v2)
  - **What they did:** Deployed LMs are reluctant to express uncertainty. When prompted to state confidence, they overclaim, with 47% errors among confident answers. Users over-rely on outputs regardless of markers, and preference annotators are biased against uncertain text.
  - **Relation:** RLHF-tuned instruct models lean toward assertive wording, so expect overclaiming by default. Users also tend not to read hedges carefully, which is a reason to make evidence levels *visible* as badges and not only as wording.
- **Band, N., Li, X., Ma, T., Hashimoto, T. (2024). "Linguistic Calibration of Long-Form Generations." ICML 2024, PMLR 235:2732–2778. [V]** — [PMLR](https://proceedings.mlr.press/v235/band24a.html); [arXiv:2404.00474](https://arxiv.org/abs/2404.00474v1)
  - **What they did:** They define linguistic calibration as long-form text that lets *readers* make calibrated probabilistic forecasts. They train Llama 2 7B with SFT and then RL using a reward from a simulated reader answering related questions. It is much better calibrated than factuality baselines, including out-of-domain (science, biomedical, biographies). — [ICML](https://icml.cc/virtual/2024/poster/32959)
  - **Relation:** A metric idea to adopt is **reader-based evaluation**. Ask a separate reader model, or humans, "Does this text claim that council A caused or influenced council B?" and measure how often a causal reading is induced. It also shows that 7B-scale training for calibration is feasible, though RL is beyond our budget.
- **Yona, G., Aharoni, R., Geva, M. (2024). "Can Large Language Models Faithfully Express Their Intrinsic Uncertainty in Words?" EMNLP 2024, pp. 7752–7764. [V]** — [ACL Anthology](https://aclanthology.org/2024.emnlp-main.443); [arXiv:2405.16908](https://arxiv.org/abs/2405.16908v2)
  - **What they did:** A response is decomposed into assertions, and each gets a *decisiveness* score derived from its hedging. Faithful response uncertainty is the gap between intrinsic confidence and decisiveness. Models answer decisively despite uncertainty, and prompting them to hedge produces unfaithful hedges.
  - **Relation:** **A metric template.** Our overclaim for a statement is decisiveness or causal strength minus the strength licensed by its evidence level, counted when positive. Adopt their assertion-level decomposition.
- **Ghafouri, B., Mohammadzadeh, S., et al. (2024). "Epistemic Integrity in Large Language Models." arXiv:2411.06528; listed as a NeurIPS 2024 workshop paper. [P: full author list not obtained]** — [arXiv](https://arxiv.org/html/2411.06528v2); [NeurIPS](https://neurips.cc/virtual/2024/106197)
  - **What they did:** A human-labeled dataset and a method for measuring *linguistic assertiveness* (over 50% lower MSE than earlier benchmarks), revealing a mismatch between assertiveness and accuracy.
  - **Relation:** A continuous assertiveness regressor is an alternative or complement to a discrete ladder.
- **Rathi, N., Jurafsky, D., Zhou, K. (2025). "Humans overrely on overconfident language models, across languages." arXiv:2507.06306 (v2 Aug 2025). [V]** — [arXiv abs](https://arxiv.org/abs/2507.06306)
  - **What they did:** Studied five languages; English, Japanese, German and Mandarin are named on the page and **Korean is not confirmed**. Epistemic marker use follows cross-linguistic norms: most uncertainty markers in Japanese, most certainty markers in German and Mandarin. Users discount Japanese hedges.
  - **Relation:** Marker inventories and reader interpretation do not transfer across languages, so we need a Korean-specific inventory and a Korean validation set.
- **Farkas et al. (2010), CoNLL-2010** (see Q2). The standard hedge-detection metrics are sentence-level F1 on "uncertain" plus cue-level and scope-level F1. — [ACL Anthology](https://aclanthology.org/W10-3001/)
- **Chen, J., Chen, W., Lin, Z., Vong, C. M. (2026). "A Judge Should Know What Changed: Construct Validity for LLM-as-a-Judge Evaluation." arXiv:2608.24419. [V]** — [arXiv abs](https://arxiv.org/abs/2608.24419)
  - **What they did:** Tested 7 judges in 4 domains. Invariance S = 0.945, but construct sensitivity R = 0.319. Judges are **less sensitive to strength edits (R_strength = 0.262) than to scope edits (0.383)**, with the same sign for all 7 judges.
  - **Relation:** **An important caution.** An LLM judge of "causal strength" will miss many strength inflations. Validate our checker with *minimal-pair* edits (e.g., "이후" ↔ "영향을 받아") and report its sensitivity.

### Inferences
- The concept to name: classic linguistic calibration is calibration to *what the model knows*. Ours is calibration to *what the evidence licenses*. The two are orthogonal. A model can be fully confident that B followed A in time and still be unlicensed to say B was influenced by A.
- Measurement can reuse:
  - Yona's assertion decomposition plus decisiveness;
  - Mielke's control-token conditioning;
  - Band's reader-based probe;
  - Chen's minimal-pair sensitivity test for validating the checker.

### Gaps
- No Korean-language linguistic calibration study was found.
- The epistemic-marker searches for Korean LLM outputs could not be run (search budget).

---

## Q5. Are there resources for Korean causal or hedging markers, or for Korean causal-relation classification?

### Takeaway
I found **no public, openly licensed Korean dataset** for causal-claim strength, for causal vs. correlational classification, or for hedge detection. What exists:
- older Korean hedge-detection papers (a tagged corpus with cue patterns, F1 78.6%; follow-ups with ML and neural models), with corpus release status unknown;
- corpus-linguistic studies of Korean hedges (-을 수 있-, -을 것이-, stacked hedges) and of causal connectives (-어서 / -니까 and their epistemic uses);
- a small causal-extraction study on car manuals.

These can seed a lexicon and annotation guidelines, but we must build a small in-domain labeled set ourselves.

### Cited Findings
- **Lee, S.-H. (이선희, Wellesley College), Lee, C.-Y. (이찬영, Yonsei University) (2019). "Formulaic Hedging Expressions in Korean: Focusing on -을 수 있- -ul su -iss- and -을 것-이- -ul kes-i-." 담화와 인지 (Discourse and Cognition) 26(3):157–179. DOI 10.15718/discog.2019.26.3.157. [V]** — [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002494496)
  - **What they did:** -을 수 있- is more than twice as frequent in an academic corpus as in a balanced written corpus. Korean hedging has complex morpho-syntactic patterns: hedges stack (-을 수 있- + -을 것이-), and indirect quotation combines with hedges (-다고 할 수 있-).
  - **Relation:** Lexicon seeds. Stacked hedges such as "~라고 볼 수 있을 것이다" need their own strength scoring, so a single-token lexicon will under-capture them.
- **정주석, 김준혁, 김해일, 오성호, 강신재 (2011). 「한국어 Hedge 문장 인식을 위한 태깅 말뭉치 및 단서어구 패턴 구축」. 한국지능시스템학회 논문지 21(6):761–766. [P: bibliographic data and result from a search-result summary of the newnonmun/KoreaScience listing; primary page not opened]** — [newnonmun listing](https://www.newnonmun.com/article=10622296)
  - **What they did:** Built a Korean hedge-tagged corpus and generalized cue-phrase patterns, reaching F1 78.6% on hedge sentence recognition.
  - Follow-ups:
    - 정주석·강신재 (2012), 「기계학습을 이용한 한국어 Hedge 문장 인식」, 한국멀티미디어학회 학술대회. [P] — [KoreaScience](https://koreascience.kr/article/CFKO201230533391207.do)
    - 임미영·강신재 (2017), 「단어 쓰임새 정보와 신경망을 활용한 한국어 Hedge 인식」, with SVM/CRF baselines vs. embeddings plus a neural network. **[U: venue not verified]**
  - **Relation:** Prior Korean *hedge detection* exists in the CoNLL-2010 style and should be cited as a foundation. Our contribution is *strength-vs-evidence calibration in generation*, not hedge detection itself. Corpus availability is unknown, so contact the authors or skip it.
- **-(e)se vs. -(u)nikka study, *International Journal of Corpus Linguistics* 10(4):469–488 (2005), by "Oh". [P: journal, volume and pages from the publisher listing in search results; author full name and exact title not verified]** — [Benjamins](https://benjamins.com/catalog/ijcl.10.4.05oh)
  - **What they did:** The causal suffixes -어서 and -니까 operate on four cognitive-discourse levels: content, epistemic, speech act and discourse. Both can access all four, with different ease.
  - **Relation:** Korean causal connectives are polysemous. -어서 is often purely sequential ("가서 보고"), and -니까 is often epistemic or speech-act. A regex on these endings will be noisy, so a classifier is needed.
- **Lee Hye-Kyung (2022), *Linguistic Research* 39(1).** A corpus analysis of sentence-final -니까 that separates epistemic causality, speech-act causality and discourse-marker uses. [P: from a search-result summary] — [Ajou repository](https://aurora.ajou.ac.kr/handle/2018.oak/32683?mode=full)
- **HCLT 2018 (제30회 한글 및 한국어 정보처리 학술대회), 「학습 데이터 확장을 통한 딥러닝 기반 인과관계 추출 모델」.** Hand-built gold causal data from car owner's manuals, with statistical expansion (+7.07 points). Release unknown. [P] — [KoreaScience PDF](https://www.koreascience.or.kr/article/CFKO201832073078549.pdf)
- **Korean relation-extraction datasets** such as KLUE-RE (30 relation types) contain *no causal label*. [P: search summary] — [Survey of Korean NLP datasets](https://arxiv.org/pdf/2112.01624)
- **AI Hub:** I found no dedicated causal or hedge dataset. A 2026 AI Hub reasoning-data project ("복합 문서 기반 지식 추론 데이터", Crowdworks consortium) is under construction and is not causal-specific. [P: news coverage] — [byline.network](https://byline.network/2026/07/7-453/)
- **Cross-lingual markers:** Rathi et al. (2025) do not confirm Korean among their languages (see Q4). — [arXiv abs](https://arxiv.org/abs/2507.06306)

### Inferences
- **A proposed Korean marker inventory, from strongest to weakest causal strength.** These are not from any single source; they are synthesized from Yu 2019's English cue table, the Korean hedge and connective studies above, and the competition's needs.
  - **Direct causal / influence (forbidden in all levels under competition rules):**
    - "영향을 받아/영향을 미쳐/영향으로"
    - "~로 인해/인하여", "~때문에", "~의 결과(로)", "~를 계기로"
    - "촉발", "견인", "파급", "전파", "확산시켰다"
    - "벤치마킹하여 도입", "~를 따라 도입", "선도하여"
  - **Hedged causal (forbidden; analogous to Yu's "conditional causal"):**
    - "영향을 받았을 가능성", "~의 영향으로 보인다/추정된다", "~로 이어졌을 수 있다"
  - **Attributed explicit reference (allowed only at E1, with a verbatim span):**
    - "B의회 ○○ 회의록에서 'A시 사례'가 언급됨", "~를 참고했다고 발언", "~에 따르면"
  - **Shared external factor co-mention (allowed only at E2, when both minutes mention the factor):**
    - "두 의회 회의록 모두 ○○법 개정을 언급"
    - Do **not** write "법 개정으로 인해 확산".
  - **Temporal-only (allowed at E3):**
    - "이후", "뒤이어", "약 ○개월 뒤", "가장 먼저 확인된 시점은"
  - **Unknown order (E4):**
    - "같은 시기(○년 ○월)", "선후를 판단할 근거가 부족"
- **Ambiguities to handle with a classifier rather than regex:**
  - "~에 따라": "according to" vs. "due to";
  - "-어서" and "-면서": sequence or simultaneity vs. cause;
  - "확산": as a forecast noun ("확산 가능성", "future diffusion likelihood", which is required output) vs. a causal verb ("확산시켰다").
- A morphological analyzer is needed to segment endings before matching. Kiwi (kiwipiepy) or Mecab-ko are common choices; **[U: tools not verified in this session]**.

### Gaps
- These searches could not be run: the 모두의 말뭉치 annotation inventories, Korean discourse-relation corpora (PDTB-style), Korean factuality or modality corpora, and recent (2023–2026) Korean LLM hedging studies.
- Release status of the 2011–2017 Korean hedge corpora is unknown.

---

## Q6. What metrics would make a "causal overclaim rate" credible (annotation scheme, agreement, automatic-detector validation)?

### Takeaway
Credibility comes from six things:
1. A **written ordinal strength ladder with examples and pre-declared ceilings per evidence level**, following Sumner, Yu and GRADE 26.
2. **Double annotation with Cohen's κ**. Precedents: κ = 0.98 and 0.95 for causal-strength labels (Yu 2019/2020) and 0.79–0.95 for generalization coding (Peters 2025).
3. **Detector validation** on a held-out human gold set, with per-class P/R/F1 and especially *recall on overclaims*.
4. A **conservative, pre-declared aggregation rule** (Yu 2020).
5. **Reporting overclaim *and* underclaim plus abstention coverage**, so that "hedge everything" is not a trivial solution.
6. **Construct-validity tests with minimal pairs**, because LLM judges are insensitive to strength edits (Chen 2026).

### Cited Findings
- **Annotation-agreement precedents:**
  - Yu et al. 2019: κ = 0.98, 2 annotators on 30 abstracts. — [PDF](https://aclanthology.org/D19-1473.pdf)
  - Yu et al. 2020: κ = 0.95 on 200 sentences. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
  - Peters & Chin-Yee 2025: κ = 0.79–0.95, including a blinded third coder. — [PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/)
- **Word-level strength is perceived inconsistently.** Haber et al. found highly heterogeneous ratings of linking-word roots. — [eScholarship](https://escholarship.org/uc/item/5c56c6gk). This argues for sentence-level labels with written guidelines rather than a fixed word list.
- **Exaggeration is defined relative to the source, with a conservative rule.** Yu 2020 counts only direct-causal from correlational-only sources, uses a headline-first aggregation, and does not count conditional causal. — [PDF](https://aclanthology.org/2020.coling-main.427.pdf)
- **Claim-level overreach can be measured by matching each claim to its source counterpart.** Isch et al. found 26.8% causal overreach at claim level. [P] — [Marginal Revolution](https://marginalrevolution.com/marginalrevolution/2026/08/overreaching-causal-language-in-the-social-sciences.html)
- **Atomic decomposition:** Min, S., Krishna, K., Lyu, X., Lewis, M., Yih, W., Koh, P., Iyyer, M., Zettlemoyer, L., Hajishirzi, H. (2023). "FActScore: Fine-grained Atomic Evaluation of Factual Precision in Long Form Text Generation." EMNLP 2023, pp. 12076–12100. It splits long text into atomic facts, scores the fraction supported, and includes a validated automatic estimator. [V] — [ACL Anthology](https://aclanthology.org/2023.emnlp-main.741/)
- **Assertion-level decisiveness vs. a reference confidence** (Yona et al. 2024). — [ACL Anthology](https://aclanthology.org/2024.emnlp-main.443)
- **Validating the automatic evaluator on a human sample** (200 samples in ESB). — [Tech Science Press](https://www.techscience.com/cmc/v89n1/68467)
- **Citation precision/recall and grounded refusals** as companion metrics (Trust-Score). — [arXiv](https://arxiv.org/abs/2409.11242v3)
- **LLM judges are less sensitive to strength edits than to scope edits** (R_strength = 0.262). — [arXiv](https://arxiv.org/abs/2608.24419)
- **Self-stated evidence grades are at chance**, so the model should not be asked to self-label the level. — [arXiv](https://arxiv.org/abs/2606.29034)

### Inferences
**Proposed metric suite.** These are my recommendations, not taken from any single paper.

- **Unit:** a *relational statement* u, i.e., an atomic statement linking two or more councils, or a council and an external factor. Decompose FActScore-style, either with rules on sentences that name two or more councils or with the LLM, then spot-check.
- **Evidence level e(u) ∈ {E1, E2, E3, E4}:** assigned deterministically by the pipeline, never by the generator.
- **Ceiling c(e):** the maximum allowed strength class. Under the competition rules no level permits causal or hedged-causal wording.
- **Causal Overclaim Rate (COR):**

  COR = #{u : s(u) > c(e(u))} / #U

  Report it overall and per evidence level, with bootstrap 95% CIs, and also a severity-weighted version, mean(max(0, s − c)).
- **Unsupported-reference rate:** the share of statements that claim an explicit reference but have no verbatim span containing the other council's name or region marker. It is checkable by string match, so no model is needed.
- **Underclaim rate:** E1 links narrated as mere co-occurrence. Report it so that over-hedging is visible.
- **Coverage / abstention rate:** the share of candidate links narrated vs. withheld or templated. Show a coverage–COR trade-off curve.
- **Detector validity:**
  - a gold set of about 300–500 generated Korean sentences, stratified by evidence level and by system;
  - 2 annotators with κ reported (target ≥ 0.8, consistent with precedents);
  - detector P/R/F1 per class and overclaim recall;
  - a **minimal-pair sensitivity set** (e.g., 100 pairs swapping "이후" ↔ "영향을 받아", or "언급하며" ↔ "벤치마킹하여"), reporting the share of pairs where the detector's verdict flips correctly (Chen 2026's construct sensitivity R).
- **Optional reader-based check** (Band 2024; the Isch reader experiment): a separate reader model or a few humans answer "이 문단은 A가 B에 영향을 미쳤다고 주장하는가?". Report the induced-causal-reading rate.

### Gaps
- I found no prior study that reports an overclaim rate *for RAG-generated text against typed evidence*, so there is no direct benchmark number to compare against.
- Annotation cost in Korean has not been estimated.

---

## Q7 (Synthesis). Novelty assessment, feasible methods with local 7B Korean models, and framing of the wow point

### Takeaway
The idea is **novel as a combination and in its evidence-type axis, but not in its components**. The closest work:
- **Fan et al. 2026 (claim-locked reporting with allowed language strength)** is the closest generation-side precedent.
- **Yu et al. 2020 / Sumner et al. 2014** supply the "strength(output) > strength(source)" overclaim definition.
- **ESB 2026 / Self-RAG** cover graded evidence → behaviour in RAG.
- **GRADE 26** is the human-practice precedent of evidence-level → mandated wording.
- **Mielke 2022 / Yona 2024** supply control-token conditioning and the decisiveness-gap metric.

The defensible claim is the first measured, enforced *evidence-type-calibrated* causal language for *inter-document diffusion narratives*, in Korean, with local models. It should not be pitched as "first to control claim strength".

### Cited Findings
- Closest generation-side precedent: claim-locked reporting with allowed language strength. — [arXiv:2608.25336](https://arxiv.org/abs/2608.25336)
- Overclaim as strength mismatch between source and derived text. — [Yu et al. 2020 PDF](https://aclanthology.org/2020.coling-main.427.pdf); [Yu et al. 2019 PDF](https://aclanthology.org/D19-1473.pdf)
- Graded evidence and abstention in RAG. — [ESB](https://www.techscience.com/cmc/v89n1/68467); [Self-RAG](https://proceedings.iclr.cc/paper_files/paper/2024/hash/25f7be9694d7b32d5cc670927b8091e1-Abstract-Conference.html)
- Certainty-graded mandated wording. — [GRADE blog on Santesso et al.](https://usblog.gradeworkinggroup.org/2020/02/research-shorts-informative-statements.html)
- Control-token calibration; decisiveness gap. — [Mielke et al. 2022](https://aclanthology.org/2022.tacl-1.50/); [Yona et al. 2024](https://aclanthology.org/2024.emnlp-main.443)
- LLMs commit the post hoc fallacy. — [Joshi et al. 2024](https://aclanthology.org/2024.emnlp-main.590)
- LLM summaries strip hedges and add causal claims. — [Isch et al. 2026 via MR](https://marginalrevolution.com/marginalrevolution/2026/08/overreaching-causal-language-in-the-social-sciences.html)
- Temperature 0 helps; an accuracy prompt backfires. — [Peters & Chin-Yee 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12042776/)
- Self-correction restores causal caution. — [Okumura 2026](https://arxiv.org/abs/2606.24370)
- LLM judges are insensitive to strength edits. — [Chen et al. 2026](https://arxiv.org/abs/2608.24419)

### Inferences

#### (a) Novelty assessment
- **What is new, to our knowledge** (based on searches up to Oct 2026; see the Gaps sections for what was not searched):
  1. A **typed evidence ladder for links between documents** in a diffusion graph: E1 explicit cross-reference with a verbatim span; E2 common external factor co-mentioned in both minutes; E3 temporal order only; E4 order unknown or simultaneous.
  2. **Level-conditioned generation** in which each level licenses a specific *non-causal* vocabulary.
  3. **A validated Korean causal/certainty-strength detector** used as a runtime checker, with regeneration or abstention.
  4. **A reported Causal Overclaim Rate**, with detector validity (κ, P/R, minimal-pair sensitivity), on Korean council minutes with a local 7B model.
- **Closest prior work and the exact difference:**
  - *Fan et al. 2026*: same "lock strength before prose" control, but the strength comes from statistical results within one study, and there is no causal/temporal relation typology and no cross-document diffusion.
  - *Yu 2019/2020, Wright & Augenstein 2021*: same overclaim definition, but post-hoc detection on human-written press releases, not generation control.
  - *Self-RAG, Trust-Align, ESB*: they control support, refusal or abstention, not causal-strength wording.
  - *Mielke, Band, Yona, Liu 2026*: they calibrate to internal confidence, not external evidence type.
  - *Joshi 2024, Isch 2026, Peters 2025*: they diagnose the failure without enforcing a fix in RAG.
- **Residual risk:** a 2025–2026 paper on "causal-language-aware RAG" or "evidence-graded summarization" in medicine or policy may exist that I did not find. The search budget ran out before queries on ALCE-style attribution with relation types, policy-diffusion NLP and Korean LLM hedging.

#### (b) Concrete method recommendations (Qwen2.5-7B-Instruct 4-bit, 8 GB GPU, Korean)
1. **Assign evidence levels deterministically, outside the LLM** (Arasteh 2026 and ESB 2026 show LLM self-grading is unreliable).
   - **E1:** the later council's passage mentions the earlier council or region name ("○○시", "○○도", "타 시도 사례") within the issue-relevant passages. Require the verbatim span.
   - **E2:** both minutes mention the same national law, decree or central-government policy. Detect with a regex on "법/시행령/조례 개정/정부 지침" and match law names.
   - **E3:** both dates are known and ordered, and neither E1 nor E2 applies.
   - **E4:** same month or session, or dates unclear.

   Only E1 permits reference statements, and only as *attributed reporting*.
2. **Claim-locked skeleton** (adopting Fan et al. 2026). Code fills each link's fixed slots: council, date, minutes title, verbatim span, evidence badge [E1–E4]. The LLM writes only connective prose within a per-level **allowed/forbidden phrase table** given in the prompt. This mirrors GRADE 26's mandated wording and Mielke's control conditioning.
3. **Decoding:** greedy or temperature 0 (Peters 2025: about 76% fewer generalizations than at 0.7). Do not add "be accurate" instructions; use explicit *causal-caution* instructions plus a self-audit pass instead (Isch 2026; Okumura 2026). Optionally add hard bans on the strongest forbidden strings through the generation API's bad-words or logits-processor option **[U: not verified in this session]**. Paraphrases can leak past bans, so the checker remains necessary.
4. **Checker (two-stage, runs on CPU or GPU within 8 GB):**
   - **Stage 1, high recall:** lexicon and morpheme patterns over a Korean morphological analysis, using the inventory in Q5.
   - **Stage 2, precision:** a small Korean encoder classifier (a KLUE-RoBERTa/KoELECTRA-class model **[U]**) fine-tuned on about 1–2K labeled sentences. Bootstrap the labels by pre-annotating with Qwen2.5-7B, then correct by hand. PET-style few-shot training is an option (Wright & Augenstein 2021).
   - Use Qwen-as-judge only as a secondary signal, because LLM judges are insensitive to strength edits (Chen 2026).
   - Distinguish *attributed quotes of speakers* (allowed) from *system assertions* (checked), following the spin-propagation finding in Yun et al. 2025.
5. **Regenerate → abstain loop** (RARR, CoVe style). On a violation, give targeted feedback (e.g., "'영향을 받아'는 E3 링크에서 금지됨 → '이후'로 서술"), regenerate up to k = 2 times, then fall back to the deterministic template sentence. Log every intervention; the log becomes part of the evidence trail.
6. **J2 forecasts:** phrase "future diffusion likelihood" with a GRADE-like certainty ladder tied to observable counts (e.g., number of councils with E1 or E3 links, recency). Run the same checker on the forecast text, because advisory contexts suppress caution (Okumura 2026). Ban present-tense generics and action-guiding claims beyond the data, in line with Peters 2025's three markers.
7. **Evaluation design for the report:**
   - Compare four systems on the same issues:
     - B0: vanilla RAG prompt;
     - B1: instruction-only ("인과관계를 단정하지 말 것");
     - B2: level-conditioned prompt plus phrase table;
     - B3: B2 + checker + regenerate/abstain.
   - Report COR (overall and per level), the unsupported-reference rate, underclaim, coverage, detector κ and P/R, and minimal-pair sensitivity.
   - Confirm that J1 tracking metrics (first appearance, propagation-path precision) do not degrade.
   - Pre-register the hypothesis that B0 has a non-zero COR concentrated at E3 (the post hoc fallacy, Joshi 2024), and report whatever is found.
8. **Stretch goal (only if time allows):** DPO on compliant vs. overclaiming pairs, following Trust-Align, which used Qwen2.5 up to 7B. QLoRA DPO for a 7B model on 8 GB is tight; treat it as optional.

#### (c) Suggested framing of the wow point
- **One-liner (KR):** "말의 세기를 근거의 종류에 묶는다 — 근거 유형 보정 생성(Evidence-Type-Calibrated Generation)." ("Bind the strength of the wording to the type of evidence.")
- **One-liner (EN):** "Claim strength ≤ evidence type: every inter-council link carries an evidence badge, the generator may only use the wording that badge licenses, and we *measure* how often it doesn't (Causal Overclaim Rate)."
- **Positioning sentence:** The work sits at the intersection of three literatures:
  1. science-communication exaggeration detection, which measures strength mismatch in human text after the fact;
  2. LLM linguistic calibration, which calibrates wording to the model's own confidence;
  3. trustworthy RAG, which checks support and abstains.

  We **calibrate to the type of external evidence, enforce it at generation time, and audit it with a validated metric**.
- **Rule-to-metric story for judges:** turn the competition rule "인과 단정 금지" (no causal assertions) into a measurable, auditable quantity. Show:
  - side-by-side B0 vs. B3 text with highlighted forbidden markers;
  - a COR bar chart per evidence level;
  - detector κ and minimal-pair sensitivity;
  - a diffusion graph whose edges are styled by evidence level (E1 solid, E2 dashed with the law name, E3 dotted arrow labelled "temporal order only", E4 undirected).
- **Honesty clause** (which strengthens the "research capability" impression): acknowledge GRADE 26 and claim-locked reporting (2026) as precedents for strength-constrained writing, Yu et al. for the overclaim definition, and Joshi et al. for the failure mode. Claim novelty only for the evidence-type axis in cross-document diffusion narratives, plus a validated Korean measurement.
- **J2 link:** the same ladder makes forecasts *logically valid*. Forecast certainty language is derived from counts of observed E1–E3 links, so a judge can trace why a forecast says "가능성이 있다" rather than "확산될 것이다" ("there is a possibility" rather than "it will spread").

### Gaps
- Not searched because the search budget ran out:
  - ALCE and attribution benchmarks;
  - policy-diffusion text-reuse NLP;
  - Korean LLM epistemic-marker studies;
  - hedge-generation papers;
  - medical "evidence-graded summarization" systems that might implement a GRADE-to-wording pipeline with LLMs.
- Not opened: the full texts of Fan et al. 2026, Isch et al. 2026 (Nature page inaccessible) and GRADE 26 (exact wording table inaccessible).
- The Korean tool and model names in (b) (Kiwi/Mecab-ko, KLUE-RoBERTa/KoELECTRA, HF bad-words option) are suggestions not verified in this session. Check their availability and licenses before use.
- I could not verify whether the competition allows training a detector on external English datasets or on manually labeled samples of the competition data. Confirm with the rules.
