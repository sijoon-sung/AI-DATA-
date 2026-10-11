# Text-based analysis of policy diffusion and ML forecasting of policy adoption across subnational governments

Scope: prior work relevant to our KISTI/NANET 2026 entry (17 Korean metropolitan councils, 2024–2025 minutes and agenda lists). The pipeline: issues from ordinance bill titles; discussion-stage and adoption-stage tracking; explicit cross-references used as evidence and as precursor features; a discrete-time hazard forecast of adoption within 6 months. In the quick leakage-free backtest, AUC was 0.71–0.73, top-3 hit rate 0.25–0.29 against about 0.09 random, Brier was no better than the base rate, and the neighbor feature was weak.

Verification legend:
- **[V]**: authors, title, venue and year confirmed on a primary or bibliographic page in this session (publisher, Crossref, KCI, institutional repository, arXiv).
- **[PV]**: partially verified. Title and venue were seen in search listings, but some metadata or claims were not checked on the source page.
- **[UV]**: unverified lead.

Process note: the shared WebSearch budget ran out partway through this task, so a few leads stayed at [PV]/[UV] and the 2022–2026 LLM sweep is less exhaustive than intended. Every claim below carries its source.

---

## Q1. Text-as-data studies of policy diffusion (foundational + 2022–2026 LLM/embedding work)

### Takeaway
Text-as-data diffusion research follows two traditions:
- **Text reuse of bills or model legislation (adoption stage).** Wilkerson et al. 2015, Burgess et al. 2016, Garrett & Jansa 2015, Linder et al. 2020 and Hansen & Jansa 2021 belong here.
- **Pre-adoption discourse.** Gilardi, Shipan & Wüest 2021 is the anchor: topic models on newspapers, with frames predicted by prior adoptions.

I found no peer-reviewed study that uses LLMs or embeddings to trace cross-jurisdiction diffusion in legislative debates or council minutes. The 2025–2026 LLM work consists of a proposal paper (CongressRA), a methods review of municipal-minutes NLP, and LLM-annotation validity studies. That is weak coverage, not a demonstrated gap: the search budget was exhausted before this sweep was complete.

### Cited Findings

**Gilardi, F., Shipan, C. R., & Wüest, B. (2021). "Policy Diffusion: The Issue-Definition Stage." *American Journal of Political Science* 65(1): 21–35. DOI 10.1111/ajps.12521. [V]** [IDEAS record](https://ideas.repec.org/a/wly/amposc/v65y2021i1p21-35.html); [author PDF via Deep Blue](https://deepblue.lib.umich.edu/handle/2027.42/166196?show=full)
- **Data:** about 52,000 newspaper paragraphs on anti-smoking laws, from 49 newspapers covering 49 U.S. states, 1996–2013. Frames are estimated with structural topic models (STM). [Deep Blue PDF](https://backend.production.deepblue-documents.lib.umich.edu/server/api/core/bitstreams/f5513b76-6b39-48be-bd16-cc06daae220f/content)
- **Key covariate:** a spatial lag of prior adoptions by "relevant" states, built from the latent diffusion network of Desmarais, Harden & Boehmke (2015). They forecast that network for 2010–13 with temporal ERGMs and report similar results using contiguous neighbors or all states. [Deep Blue PDF](https://backend.production.deepblue-documents.lib.umich.edu/server/api/core/bitstreams/f5513b76-6b39-48be-bd16-cc06daae220f/content)
- **Result:** prior adoptions predict frames about the policy's concrete, practical implications but not frames about its normative justification. The authors argue that diffusion can occur without adoption, because "adoptions are rare, whereas consideration of new policies occurs frequently." [IDEAS](https://ideas.repec.org/a/wly/amposc/v65y2021i1p21-35.html); [Deep Blue PDF](https://backend.production.deepblue-documents.lib.umich.edu/server/api/core/bitstreams/f5513b76-6b39-48be-bd16-cc06daae220f/content)
- **Relation to our project: closest conceptual prior work (novelty threat on the "discussion stage" idea).** We differ in three ways:
  - We use council minutes, the policymakers' own speech, rather than newspapers.
  - We cover many bottom-up issues rather than one pre-chosen policy.
  - We forecast adoption from discussion, where they explain frames from adoption.
  - **Method to adopt:** split discussion signals into "practical/consequence" mentions (effects, budget, cases) and "normative" mentions.

**Wilkerson, J., Smith, D., & Stramp, N. (2015). "Tracing the Flow of Policy Ideas in Legislatures: A Text Reuse Approach." *AJPS* 59(4): 943–956. DOI 10.1111/ajps.12175. [V]** [UW page](https://www.polisci.washington.edu/research/publications/tracing-flow-policy-ideas-legislatures-text-reuse-approach); [preprint](https://ccs.neu.edu/home/dasmith/wilkerson-smith-stramp-AJPS.pdf)
- Tracks policy ideas rather than bills through the U.S. Congress. It aligns bill sections with plagiarism-style text-reuse methods and a similarity threshold. Example: H.R. 3590 grew from a 7-page bill into the ACA (900+ pages). [AJPS blog](https://ajps.org/2015/06/10/cracking-the-black-box-of-lawmaking/)
- **Relation: method to adopt.** Use section-level alignment if ordinance full texts are available. We differ in working cross-jurisdiction rather than within one legislature, and on speech rather than bill text.

**Linder, F., Desmarais, B., Burgess, M., & Giraudy, E. (2020). "Text as Policy: Measuring Policy Similarity through Bill Text Reuse." *Policy Studies Journal* 48(2): 546–574. DOI 10.1111/psj.12257. [V]** [PSU Pure](https://pure.psu.edu/en/publications/text-as-policy-measuring-policy-similarity-through-bill-text-reus/); [SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2812607)
- Text-reuse similarity on about 500,000 U.S. state bills. It is validated three ways: sponsor ideology, NCSL topic grouping, and correlation with policy diffusion network ties between states. [PSU Pure](https://pure.psu.edu/en/publications/text-as-policy-measuring-policy-similarity-through-bill-text-reus/)
- **Relation: method to adopt.** Pairwise council-to-council text/title reuse in the training window can serve as a dynamic "tie" feature, which is an alternative to geography.

**Burgess, M., Giraudy, E., Katz-Samuels, J., Walsh, J., Willis, D., Haynes, L., & Ghani, R. (2016). "The Legislative Influence Detector: Finding Text Reuse in State Legislation." *Proc. 22nd ACM SIGKDD*, 57–66. DOI 10.1145/2939672.2939697. [V]** [Crossref](https://api.crossref.org/works/10.1145/2939672.2939697); [DSSG project page](https://dssgfellowship.org/lid/)
- **Method:** Elasticsearch/Lucene pre-filters the top 100 candidates, then Smith-Waterman local alignment. The corpus is more than 500,000 state bills plus about 2,400 model bills. [DSSG](https://dssgfellowship.org/lid/)
- **Counts:** 45,405 bill-to-bill and 14,137 model-to-bill reuse instances. These figures come from a search summary of U-M coverage and were not checked on the paper. [U-M news](https://si.umich.edu/about-umsi/news/lobbyists-model-legislation-unmasked)
- **Relation: method to adopt.** The two-stage "retrieve, then align" design suits verbatim-evidence retrieval over our 3.56M passages. Our target is citations in speech, not copied statute text.

**Garrett, K. N., & Jansa, J. M. (2015). "Interest Group Influence in Policy Diffusion Networks." *State Politics & Policy Quarterly* 15(3): 387–417. DOI 10.1177/1532440015592776. [V]** [Cambridge](https://resolve.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/interest-group-influence-in-policy-diffusion-networks/2E440AE9A7838D1841E229B78D81F785)
- Builds text similarity networks over bills on abortion insurance restrictions and self-defense statutes. Interest-group model legislation, not early-adopting states, sits at the center of the networks. [Cambridge](https://resolve.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/interest-group-influence-in-policy-diffusion-networks/2E440AE9A7838D1841E229B78D81F785)
- **Relation: differentiation and a caution.** In Korea the analog of model bills is template ordinances and national mandates (e.g., 행안부 표준조례안). Simultaneous bursts may be template-driven, not peer-to-peer. Do not narrate them as "flow from council A to B."

**Hansen, E. R., & Jansa, J. M. (2021). "Complexity, resources and text borrowing in state legislatures." *Journal of Public Policy* 41(4): 752–775. DOI 10.1017/S0143814X20000252. [V]** [Cambridge](https://www.cambridge.org/core/journals/journal-of-public-policy/article/abs/complexity-resources-and-text-borrowing-in-state-legislatures/A402D9FC6F0330BDE6F64989051F5A08)
- Covers 18 policies across 50 states, 1983–2014. Complex policies are rewritten more than simple ones, and high-resource legislatures rewrite more. [Cambridge](https://www.cambridge.org/core/journals/journal-of-public-policy/article/abs/complexity-resources-and-text-borrowing-in-state-legislatures/A402D9FC6F0330BDE6F64989051F5A08)
- **Relation:** the same policy appears under different titles, which supports clustering on embeddings rather than exact title matching.

**Jansa, J. M., et al. (2025). "Linking policy design and policy diffusion to advance both theories: Evidence from the elements, attributes, and adoptions of Uniform Law Commission model legislation." *Policy Studies Journal* 53(3). [PV]** [Wiley](https://onlinelibrary.wiley.com/doi/full/10.1111/psj.12591)
- The title and venue appeared in search listings. A search summary named Mallinson as co-author, but the page returned 403, so the co-author and the method were not verified.
- **Relation:** recent evidence that policy design elements matter for diffusion. Background only.

**Collingwood, L., et al. (2019). "Sustained Organizational Influence: American Legislative Exchange Council and the Diffusion of Anti-Sanctuary Policy." *Policy Studies Journal*. DOI 10.1111/psj.12284. [PV]** [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/psj.12284)
- Per the search snippet, ALEC had an "overwhelming influence" on the introduction of anti-sanctuary bills.
- **Relation:** a pre-adoption (introduction) stage modeled as an outcome.

**2022–2026 LLM / embedding / NLP-on-minutes work found**
- **Loffredo, J. R., & Yun, S. (2025). "Agent-Enhanced Large Language Models for Researching Political Institutions." arXiv:2503.13524. [V]** [arXiv](https://arxiv.org/abs/2503.13524)
  - Proposes CongressRA, an agentic RAG system over bill-summary embeddings.
  - The full text, seen only via a search snippet, lists policy diffusion as one possible application: vector DB, semantic search, text-similarity functions, and possibly transcribed floor speeches. No empirical diffusion results. [arXiv PDF](https://arxiv.org/pdf/2503.13524)
  - **Relation:** a design-level novelty threat only. Our system actually runs on minutes.
- **Campos, R., Evans, J. P., Isidro, J. M., Marques, M., Cunha, L. F., Jorge, A., Nunes, S., & Guimarães, N. (2026). "NLP for Local Governance Meeting Records: A Focus Article on Tasks, Datasets, Metrics and Benchmark." arXiv:2602.08162. [V]** [arXiv](https://arxiv.org/abs/2602.08162)
  - Reviews segmentation, entity extraction and summarization for council minutes. It does not discuss cross-municipality tracking or diffusion.
  - Related datasets: CitiLink-Minutes, 120 Portuguese municipal minutes from 2021–24 [arXiv](https://arxiv.org/html/2602.12137); MeetingBank.
  - **Relation:** supports our differentiation, since minutes-NLP has not been connected to diffusion.
- **Nakamura, K., Tan, J. L., & Yean, G. (2026). "Observational Equivalence of LLM and Human Annotation." arXiv:2609.22133. [V]** [arXiv](https://arxiv.org/abs/2609.22133)
  - Compares 10 LLMs, 3 experts and 165 crowd workers on 14 political-science coding tasks. LLM-expert agreement is comparable to expert-expert agreement, and disagreement concentrates on ambiguous rules.
  - **Method to adopt:** clear codebook rules for "explicit cross-reference" and evidence levels; use cross-LLM disagreement to flag ambiguous passages for human review.
- **"Measuring policy diffusion intensity: A text-driven analysis of government documents." *Information Processing & Management* (2025), pii S0306457325003243. [PV]** [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S0306457325003243)
  - Per the search snippet: a two-dimensional text-based indicator of diffusion intensity for Chinese city low-carbon policies. Authors and details were not verified (403).
  - **Relation:** a possible novelty threat on "text-measured diffusion" at the subnational level, but it uses government documents and does not forecast. Worth a manual check.
- **Suter et al. (2025). "When Politicians Talk AI: Issue-Frames in Parliamentary Debates Before and After ChatGPT." *Policy & Internet*. [PV]** [Wiley](https://onlinelibrary.wiley.com/doi/full/10.1002/poi3.70010)
  - BERTopic plus qualitative content analysis of parliamentary frames. Not diffusion; a methods analog.

### Inferences
- The discussion-stage idea has a clear pedigree in Gilardi et al. 2021. We should cite it as the conceptual anchor rather than claim the idea as new. Our novelty is operational: minutes instead of media, all 17 councils, many issues, prospective forecasting, and verbatim evidence.
- Text-reuse methods are adoption-stage tools. With titles only, our reuse signal is weak. If full ordinance texts or bill summaries exist in the agenda data, a LID-style "retrieve, then align" step would strengthen both evidence and ties.

### Gaps
- No peer-reviewed 2022–2026 study found that uses LLMs or sentence embeddings to trace diffusion through legislative debates or council minutes. This rests on a budget-limited search; a manual ACL Anthology / Google Scholar check for "policy diffusion" + "embedding"/"LLM" is advised.
- Burgess et al. reuse counts and the IP&M 2025 paper's authors were not confirmed on the source pages.

---

## Q2. ML/statistical forecasting of policy adoption: SPID, EHA, pooled EHA, networks, and benchmarks for AUC 0.71–0.73

### Takeaway
The policy-diffusion literature is overwhelmingly explanatory. Its standard workhorse is the discrete-time logit/Cox EHA, extended in three ways:
- pooled EHA with random coefficients;
- latent networks (NetInf → NEHA);
- the SPID database of 728 policies.

I found **no study reporting out-of-sample AUC for subnational adoption forecasting**. Connor & Clauset explicitly call the field "largely retrospective and descriptive" (snippet). So our backtest has no published benchmark to beat, and the leakage-free out-of-sample design is itself a contribution.

Two recent findings fit our weak-neighbor result:
- Since 2000, party alignment beats geographic proximity (DellaVigna & Kim).
- Neighbor effects are unstable early in the diffusion life course (Mallinson & Jansa 2026).

### Cited Findings

**Berry, F. S., & Berry, W. D. (1990). "State Lottery Adoptions as Policy Innovations: An Event History Analysis." *APSR* 84(2): 395–415. [V]** [Cambridge](https://resolve.cambridge.org/core/journals/american-political-science-review/article/abs/state-lottery-adoptions-as-policy-innovations-an-event-history-analysis/9B4EAF46DD866B9CEFFB6CA36861103A); [RePEc](https://ideas.repec.org/a/cup/apsrev/v84y1990i02p395-415_19.html)
- Introduced EHA to unify internal determinants and regional diffusion. Non-adopters are the risk set, observed yearly.
- **Relation:** our discrete-time hazard (council × issue × 6-month period, risk set = non-adopters) is the direct descendant.

**Boehmke, F. J., Brockway, M., Desmarais, B. A., Harden, J. J., LaCombe, S., Linder, F., & Wallach, H. (2020). "SPID: A New Database for Inferring Public Policy Innovativeness and Diffusion Networks." *PSJ* 48(2): 517–545. DOI 10.1111/psj.12357. [V]** [USM Aquila](https://aquila.usm.edu/fac_pubs/19108); [Iowa IRO](https://iro.uiowa.edu/esploro/outputs/journalArticle/SPIDA-New-Database-for-Inferring-Public/9983982715902771)
- 728 policies coded by topic. Two uses: static and dynamic innovativeness scores, and latent diffusion networks.
- **Relation: method to adopt.** A council "innovativeness" score, i.e., its historical share of early adoptions computed only from training-window data, is a cheap and strong feature.

**Desmarais, B. A., Harden, J. J., & Boehmke, F. J. (2015). "Persistent Policy Pathways: Inferring Diffusion Networks in the American States." *APSR* 109(2): 392–406. DOI 10.1017/S0003055415000040. [V]** [RePEc](https://ideas.repec.org/a/cup/apsrev/v109y2015i02p392-406_00.html); [PSU Pure](https://pure.psu.edu/en/publications/persistent-policy-pathways-inferring-diffusion-networks-in-the-am/)
- Infers a latent state-to-state network from 187 policies. The 2014 working paper lists as a contribution that "the network can improve conventional statistical models of state policy adoption." [2014 WP, per search snippet](https://myweb.uiowa.edu/fboehmke/shambaugh2014/papers/desmarais_etal_2014.pdf)
- The user's premise that "pathways improve prediction" is only **partially supported**:
  - I could not confirm an out-of-sample AUC in the published article (WP not retrievable; host offline).
  - A 2019 Desmarais talk abstract says adding networks "improves model fit for some, but not all" of six replicated models. [Princeton QAPS](https://qaps.princeton.edu/events/colloquium-bruce-desmarais)
  - Gilardi et al. note that the network shows diffusion most commonly runs between **non-contiguous** states. [Deep Blue PDF](https://backend.production.deepblue-documents.lib.umich.edu/server/api/core/bitstreams/f5513b76-6b39-48be-bd16-cc06daae220f/content)
- **Relation:** consistent with our weak regional-neighbor feature. Empirical ties beat geography.

**Harden, J. J., Desmarais, B. A., Brockway, M., Boehmke, F. J., LaCombe, S. J., Linder, F., & Wallach, H. (2023). "A Diffusion Network Event History Estimator." *Journal of Politics* 85(2): 436–452. DOI 10.1086/723804. [V]** [PSU Pure](https://pure.psu.edu/en/publications/a-diffusion-network-event-history-estimator/)
- NEHA embeds latent network inference inside discrete-time EHA. The inferred ties capture targeted relationships that standard covariates miss.
- **Relation: method to adopt in light form.** Learn council-to-council "leader→follower" weights from the training window, e.g., how often council j adopted within k months after council i, and use the weighted prior-adopter exposure as a feature. With 17 councils and 2 years of data, regularize heavily.

**Kreitzer, R. J., & Boehmke, F. J. (2016). "Modeling Heterogeneity in Pooled Event History Analysis." *SPPQ* 16(1): 121–141. DOI 10.1177/1532440015592798. [V]** [Cambridge](https://resolve.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/modeling-heterogeneity-in-pooled-event-history-analysis/40C485C84564193560825BAEE2C6D2D3)
- Monte Carlo study plus 29 antiabortion policies. Multilevel models with random coefficients outperform the alternatives when effects vary by policy.
- **Relation: method to adopt.** Our pooled model across issues should let slopes vary by issue type (instrument/theme layer): mixed-effects logit, or GBM with issue-type interactions.

**Mallinson, D. J. (2021). "Who Are Your Neighbors? The Role of Ideology and Decline of Geographic Proximity in the Diffusion of Policy Innovations." *PSJ* 49(1): 67–88. [V]** [PSU Pure](https://pure.psu.edu/en/publications/who-are-your-neighbors-the-role-of-ideology-and-decline-of-geogra/)
- Pooled EHA over 556 policies, 1960–2014. Contiguous-neighbor influence declines over time while ideological similarity stays stable; polarization conditions both cues.
- **Relation:** supports a weak neighbor feature and suggests adding a political-similarity feature.

**DellaVigna, S., & Kim, W. "Policy Diffusion and Polarization across U.S. States." *Review of Economic Studies* (OUP URL path vol. 93, issue 3, p. 1602; the July 2025 accepted version was read). [V for authors, title and journal; volume/issue inferred from the URL]** [OUP](https://academic.oup.com/restud/article-abstract/93/3/1602/8263742); [accepted PDF](https://www.restud.com/wp-content/uploads/2025/08/PolicyDiffusion2025-07-21_main.pdf)
- 602 state policies (SPID plus 53 policies from NBER papers), 1950s–2010s. Logit hazard over non-adopters with policy-by-decade baseline hazards and "closest third of states" exposure measures. [accepted PDF](https://www.restud.com/wp-content/uploads/2025/08/PolicyDiffusion2025-07-21_main.pdf)
- **Findings:**
  - 1950–2000 diffusion is best predicted by proximity and similar voter preferences.
  - Since 2000, party alignment is the strongest predictor and adoption is faster.
  - State capacity does not predict innovation.
  - Demographic similarity coefficient: about 0.20–0.23.
- In my text scan of the July 2025 version I found no AUC or out-of-sample metric; only pseudo-R².
- **Relation: feature to adopt.** "Exposure among same-party-controlled councils," with party control coded from in-period data, if the competition rules allow external covariates.

**Mallinson, D. J., & Jansa, J. M. (2026). "When Is the Right Time to Do a Policy Diffusion Study?" *SPPQ* 26(1): 83–102. DOI 10.1017/spq.2025.10012. [V]** [Cambridge](https://www.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/when-is-the-right-time-to-do-a-policy-diffusion-study/0C1EE5747165B5745B46F62AE93EF058)
- Re-estimates EHA on 83 SPID policies, each adopted by at least 42 states, as the observation window grows. The key findings are neighbor and relative-ideology effects, which "can shift in size, direction, and significance." [Cambridge](https://www.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/when-is-the-right-time-to-do-a-policy-diffusion-study/0C1EE5747165B5745B46F62AE93EF058)
  - Estimates move a lot until roughly 20 adopters.
  - Only 22 of 83 policies (27%) ever reached p<0.05 for neighbor adoption.
  - Cox models replicate the pattern.
  - Recommendation: state the life-course position, avoid generalizing from incomplete histories, and use partial pooling.
- **Relation: important caveat for us.** With only 17 units and a 2-year window, every issue is "incomplete diffusion." Pool across issues, report uncertainty, and frame neighbor findings as descriptive.

**Matthews, A. A., & Boehmke, F. J. (2026, in press). "Researchers in the Laboratories of Democracy: A Quarter Century of Innovations in Studying Policy Diffusion in State Politics & Policy Quarterly." *SPPQ*. DOI 10.1017/spq.2026.10020. [V]** [Buffalo ResearchConnect](https://researchconnect.buffalo.edu/en/publications/researchers-in-the-laboratories-of-democracy-a-quarter-century-of/)
- A 25-year review of SPPQ diffusion work. Useful as a current citation for the state of the field.

**Connor, N., & Clauset, A. (2018). "Predicting the outcomes of policy diffusion from U.S. states to federal law." arXiv:1810.08988. [V]** [arXiv](https://arxiv.org/abs/1810.08988)
- Predicts whether, and after how many state adoptions, a state policy becomes federal law.
  - The cumulative number of state adoptions is "reasonably predictive" of timing.
  - Initiating-state traits (wealth, urbanicity, liberalism) are not.
  - The abstract page reports no AUC. The search snippet of the PDF says past research is "largely retrospective and descriptive." [arXiv PDF](https://arxiv.org/pdf/1810.08988)
- **Relation:** a rare forecasting paper. "Cumulative adopters so far" should be a core feature.

**McGuire, S. K., & Delahunt, C. B. (2020). "Predicting United States Policy Outcomes with Random Forests." INET Working Paper. [V]** [INET](https://www.ineteconomics.org/research/research-papers/predicting-united-states-policy-outcomes-with-random-forests)
- Random forests on the Gilens dataset reach about 70% balanced accuracy on holdout, about 20 points above chance, including retrodiction from pre-1997 to post-1997 cases. [INET](https://www.ineteconomics.org/research/research-papers/predicting-united-states-policy-outcomes-with-random-forests)
- **Relation:** the only out-of-sample "policy outcome" ML number I found. It is a different task (federal policy change), so it is only a loose reference point.

**LaCombe, S., & Boehmke, F. J. "Chapter 20: Learning and Diffusion Models" (2019 draft for a SAGE methods handbook). [PV: author draft read; book metadata not confirmed]** [author PDF](https://www.scottlacombe.com/uploads/1/2/0/5/120596042/sage_pub.pdf)
- A methods overview of EHA, dyadic and network approaches. My text scan found no discussion of out-of-sample prediction, AUC or cross-validation, which is consistent with the field's explanatory focus.

### Inferences
- **Benchmarking 0.71–0.73.** No published AUC benchmark exists for this task. The fairest comparisons are internal baselines on the same split:
  - the base rate;
  - cumulative-adopter count only (Connor & Clauset style);
  - neighbor only (Berry & Berry style);
  - full model.

  A model that beats "cumulative adopters only" by a significant margin is the meaningful claim. Reporting the AUC CI and a top-k lift of about 3× random is already stronger than most diffusion papers, which report no predictive validation.
- **Brier no better than base rate.** This is expected with a 1.3–1.5% base rate and an uncalibrated logit. Add:
  - the Brier skill score against base rate and against a "cumulative-adopters" model;
  - PR-AUC, which is more informative for rare events;
  - calibration with isotonic or Platt scaling on a validation slice;
  - a reliability plot.
- **Near-random within bursts.** Consistent with model-legislation/mandate-driven simultaneous adoption (Garrett & Jansa) and vertical pressure (Korean studies, Q4). Within-burst order is probably not predictable from horizontal signals.
- **Weak neighbor AUC (0.53–0.56).** Matches Mallinson 2021, DellaVigna & Kim (post-2000) and Mallinson & Jansa 2026. In Korea, Kim & Lee 2016 found the 광역-jurisdiction path stronger than contiguity (Q4). For metropolitan councils, "same macro-region" (수도권/충청/호남/영남/강원·제주) or party alignment may beat contiguity.

### Gaps
- No verified paper reports AUC for state, provincial or municipal adoption forecasting. Possible leads not checked because the search budget ran out:
  - COVID-19 policy-timing EHA studies;
  - Chinese city-level ML diffusion papers;
  - NetworkInference package vignettes (Linder & Desmarais), which extend the 187-policy example with SPID. [CRAN vignette](https://packages.oit.ncsu.edu/cran/web/packages/NetworkInference/vignettes/tutorial_vignette.html)
- Whether the published Desmarais et al. 2015 article contains a holdout test could not be confirmed.

---

## Q3. Do explicit references to other jurisdictions predict subsequent adoption ("precursor" signals)?

### Takeaway
Evidence that policymakers **look at and cite** other jurisdictions is solid:
- legislative research briefs (Glick & Friedland);
- parliamentary debates (De Ruiter & Schalk);
- issue framing after others adopt (Gilardi et al.).

I found **no study testing whether explicit references in debate predict a later adoption by the referencing jurisdiction**. That predictive link is open, and our cross-reference "precursor signal" feature plus its backtest would be a first-of-kind empirical test, as far as this search could establish. One counterpoint matters: Parinandi et al. find that external ideological cues matter **more at adoption than at earlier stages** (cosponsorship). Pre-adoption signals may therefore be noisier than adoption-stage ones.

### Cited Findings

**Glick, D. M., & Friedland, Z. (2014). "How Often Do States Study Each Other? Evidence of Policy Knowledge Diffusion." *American Politics Research* 42(6): 956–985. [PV: citation from a reference list and abstract listings; Friedland's first name not confirmed]** [MetaTOC listing](https://www.metatoc.com/papers/32978-how-often-do-states-study-each-other-evidence-of-policy-knowledge-diffusion); [Glick's LSE blog summary](https://blogs.lse.ac.uk/usappblog/2014/05/05/state-policymakers-tend-to-look-for-lessons-from-their-neighbors-and-other-innovative-states/); [LSE Research Online](https://researchonline.lse.ac.uk/id/eprint/58900)
- Uses policy research briefs written for legislators. The briefs frequently discuss other states' policies, and the states studied are disproportionately neighbors and innovative states. Officials use other states' rules as inputs rather than copying them wholesale.
- Per the search summary of Glick's blog, the design follows 2 states across about 60 issues, with information-gathering, not adoption, as the outcome.
- **Relation: closest prior work for "explicit cross-references."** We go further in three ways:
  - all 17 councils;
  - floor and committee speech, not staff briefs;
  - a test of whether references precede adoption.

**De Ruiter, R., & Schalk, J. (2017). "Explaining cross-national policy diffusion in national parliaments: A longitudinal case study of plenary debates in the Dutch parliament." *Acta Politica* 52(2): 133–155. DOI 10.1057/ap.2015.29. [V for metadata via Crossref; findings from search snippet]** [Crossref](https://api.crossref.org/works/10.1057/ap.2015.29); [Springer](https://link.springer.com/article/10.1057/ap.2015.29)
- Counts MPs' references to other countries' policies in Dutch Lower House debates on education and environment, 1995–2012. References follow a punctuated-equilibrium pattern and favor larger countries and EU members.
- **Relation:** a direct methodological analog (references in debate as a diffusion measure). It is cross-national and descriptive, with no adoption forecasting. Korean analog: Seoul and Gyeonggi are likely the most-cited "large" councils, so test this and use it as a narrative point.

**Parinandi, S. C., Langehennig, S., & Trautmann, M. (2021). "Which Legislators Pay Attention to Other States' Policies? Comparing Cosponsorship to Floor Voting in the Diffusion of Renewable Portfolio Policy." *PSJ* 49(2) (article begins p. 408). [V: author PDF read]** [author PDF](https://nebula.wsimg.com/a145a2ec1cfcd9ffa94759cec84d424c?AccessKeyId=E8ED45F0B560ECF1108E&disposition=0&alloworigin=1)
- Legislator-level renewable portfolio standard (RPS) data. The ideological-similarity cue from adopting states matters more at the floor-vote adoption stage than at cosponsorship, the earlier stage. The paper notes that diffusion research has rarely compared stages.
- **Relation:** pre-adoption signals are not guaranteed to be stronger. Report honestly whether discussion and cross-reference features add lift over adoption-count features.

**Gilardi, Shipan & Wüest (2021)** (see Q1): prior adoptions predict the **content** of pre-adoption discourse, specifically practical-consequence frames. This is the reverse direction from our test (discourse → adoption) and complements it. [IDEAS](https://ideas.repec.org/a/wly/amposc/v65y2021i1p21-35.html)

**Butler, D. M., Volden, C., Dynes, A. M., & Shor, B. (2017). "Ideology, Learning, and Policy Diffusion: Experimental Evidence." *AJPS* 61(1): 37–49 (online 2015). [V for metadata via Crossref; findings not read this session]** [Crossref](https://api.crossref.org/works/10.1111/ajps.12213)
- An experiment with legislators on how ideology conditions learning from other governments' policies. Details were not verified here.
- **Relation:** a reason to tag who is cited (same party, same region) in cross-reference evidence.

**Stage-comparison studies (proposal vs adoption)**
- The anti-protest-bills dyadic EHA (2017–2021) finds that oil and gas lobbyists are associated with proposal but not with passage. [PV: snippet only] [ScienceDirect](https://www.sciencedirect.com/science/article/abs/pii/S2214629626000988)
- Collingwood et al. 2019 on ALEC and the introduction of anti-sanctuary bills (Q1). [Wiley](https://onlinelibrary.wiley.com/doi/10.1111/psj.12284)

### Inferences
- Our cross-reference feature can be framed as an operationalization of policy learning at the discussion stage. An example: speech in council X citing council Y's enacted ordinance on issue k at time t, followed by adoption by X. If it adds out-of-sample lift, that is a novel empirical result. Even a null result is informative, given Parinandi et al.
- **Expected bias.** References may be reactive: councils cite others when a bill is already being drafted. Measure the lead time distribution (reference → adoption) and exclude references within the same session as the bill's committee review. This keeps the feature a genuine precursor and avoids leakage.

### Gaps
- No study found that tests "reference → later adoption" quantitatively for any level of government. Glick & Friedland's full text, including any reference–adoption link, was not read.

---

## Q4. Korean research: 조례/정책 확산 사건사분석 and text mining of council minutes

### Takeaway
Korean diffusion research uses EHA (logit/Cox/panel logit) on **one or a few pre-selected ordinances or policies**, mostly at the 기초 level, for explanation, not forecasting. Recurring findings:
- **Vertical pressure** (national government, 광역→기초) matters.
- **Neighbors/prior adopters** matter.
- **Political orientation and network ties** (party, sister-city) matter.
- The **광역 jurisdiction path outperforms contiguity**.

On text mining, Korean work analyzes **National Assembly** minutes (topic models, WORDFISH). I found no peer-reviewed text-mining or diffusion study of **local council minutes** across all 17 metropolitan councils. Infrastructure is emerging: NANET's 발언 빅데이터 and a 2026 political AI DB of council minutes.

### Cited Findings

**이정철·허만형 (2016). 「주민참여예산제도의 정책확산에 관한 연구: 사건사분석 모형을 중심으로」. 『정책분석평가학회보』 26(2): 29–58. DOI 10.23036/kapae.2016.26.2.002. [V]** [CAU ScholarWorks](https://cau.scholarworks.kr/handle/2019.sw.cau/8114?mode=full)
- Two stages: first checks diffusion features (S-curve, geographic clustering), then applies EHA.
  - External drivers: the number of neighboring prior adopters, and national pressure to adopt.
  - Internal drivers: prior-year fiscal self-reliance and the political orientation of the local government head.
- **Relation:** classic Korean EHA benchmark (explanatory). Supports a "national mandate/pressure" feature.

**이대웅·권기헌 (2014). 「정책확산의 영향요인 분석: 사회적기업 조례제정을 중심으로」. 『한국정책학회보』 23(2): 93–120. [V]** [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001890336)
- Social enterprise ordinances in 56 local governments in Seoul and Gyeonggi, 2009–2012. Kaplan–Meier, then panel logit EHA. Sister-city ties and same-party networks both have significant positive effects.
- **Relation:** Korean evidence that network and party ties beat geography. Supports a party-alignment feature.

**김진영·이석환 (2016). 「정책확산의 경로에 대한 정책결정자의 주관적 인식과 객관적 계량분석 결과의 비교」. 『한국공공관리학보』 30(4): 249–270. DOI 10.24210/kapm.2016.30.4.009. [V]** [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002190568)
- Topic: 출산장려금 (birth subsidy), not a single ordinance case. This may differ from what the brief assumed.
  - Survey: policymakers say they look first at socio-economically similar governments, then the same 광역 jurisdiction, then contiguous ones, then nearby ones.
  - EHA: the 광역-jurisdiction path has the largest and most significant coefficient; contiguity is the weakest.
  - Advice: test at least two path definitions.
- **Relation:** strong local support for our weak contiguity feature. At the 광역 level, test "same macro-region" and socio-economic similarity paths instead.

**이석환·이승모 (2021). 「광역자치단체 공공갈등 관리제도의 확산」. 『한국지방자치학회보』 33(4): 203–229. DOI 10.21026/jlgs.2021.33.4.203. [V]** [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002801609)
- **The closest Korean analog in unit of analysis:** metropolitan and provincial governments. Public conflict-management ordinances, 2007–2020, Cox proportional hazards.
  - 광역 governments led adoption; top-down diffusion is more likely than bottom-up.
  - National diffusion occurred.
  - Innovativeness, administrative capacity, the head's ideology and citizen participation are significant.
- **Relation:** single-policy, explanatory. Supports "innovativeness" and executive-ideology features.

**장석준·노종호·김대진 (2015). 「정책유형별 정책혁신의 선도자와 정책확산의 양상에 관한 연구: 지방자치단체의 혁신 조례를 중심으로」. 『정부학연구』 21(3): 221–260. DOI 10.19067/jgs.2015.21.3.221. [V]** [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002069217)
- Eight innovative ordinances classified by Lowi's typology. Leaders differ somewhat by type, but there is no clean type-specific diffusion pattern.
- **Relation:** precedent for our two-layer (instrument × theme) issue taxonomy. Our version is data-driven and much larger.

**Kim, Doo-Rae (2013). "Local Government Policy Diffusion in a Decentralised System: Childbirth Support Policy in South Korea." *Local Government Studies* 39(4): 582–599. DOI 10.1080/03003930.2012.726200. [V]** [Korea Univ. repository](https://scholar.korea.ac.kr/handle/2021.sw.korea/102486)
- Horizontal mechanisms "considerably outperform" internal factors. Central government influence is positive and conditional: it stimulates horizontal interaction.
- **Relation:** an English-language Korean citation for international readers.

**Korean text analysis of minutes (non-local)**
- **이현출·장재호·김경태 (2020).** 「국회 회의록 토픽분석을 통한 상임위원회 갈등구조 분석: 제20대 국회 전반기 보건복지위를 중심으로」. 『한국정당학회보』 19(2): 131–167. DOI 10.30992/KPSR.2020.06.19.2.131. **[V]** Topic modeling of committee minutes (16 topics); conflict structure by party, topic, period and member. [KCI](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002604780)
- **이성우·곽병훈·이창언·오수길 (2015).** 「지방의원의 질적 평가 활동 가능성 탐색 - 서울시의회를 사례로」. 『한국비교정부학보』 19(1): 247–270. DOI 10.18397/kcgr.2015.19.1.247. **[V]** Uses Seoul Metropolitan Council minutes illustratively and qualitatively, not computationally. [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART001981908)
- KCI also lists 「텍스트 분석 방법론을 활용한 국회 정책 의제의 이념성향 분석」, WORDFISH on the 법사위 minutes of the 16th–19th National Assembly. **[PV]** [KCI](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002358200)

**Infrastructure / practitioner systems**
- **국회도서관 「발언 빅데이터」**: National Assembly plus local council minutes. It lists 39,547 minutes and 16,714,740 speech records; council options shown include Seoul, Busan, Ulsan and Gyeongnam. It supports search by speaker, law/ordinance and keyword, Excel download with context, and pilot extractive summaries of speeches over 500 characters. **[V]** [dataset.nanet.go.kr](https://dataset.nanet.go.kr/)
  - **Relation:** this is the competition host's own service. Our project adds what it lacks: cross-council issue linking, stage tracking, forecasting and evidence grading.
- **News, 2026-04-03 (시대일보 via Nate).** Headline seen in search results: "이준석의 '정치 실험'…지방의회 회의록 21만건 DB화, AI로 정책 설계". The page text was garbled, and the figure seems to be about 216,561 records. No evidence it does cross-council diffusion tracking or forecasting. **[PV]** [Nate News](https://m.news.nate.com/view/20260403n24344)
  - **Relation:** a practitioner-level novelty threat to "AI over council minutes," not to diffusion forecasting.

**Unverified Korean leads** (seen only in reference lists or snippets):
- 김태은 (2020), 「우리나라 광역자치단체 빅데이터 정책의 확산」, 『한국공공관리학보』 34(1). [UV]
- 「지방정부의 정책 도입 결정요인에 관한 연구: 자살예방 조례를 중심으로」, 『지방정부연구』 22(2): 281–301 (2018). Uses 광역 ordinance adoption as a vertical-diffusion variable. [PV: header seen] [KLOG PDF](http://www.klog.or.kr/data/file/library_journal/3422181213_7ipYV0Qz_12ECA095EB8BA4ECA095_EBACB8EC8AB9EBAFBC_EB8298ED839CECA480.pdf)
- 「지방자치단체 정책확산의 상이성 비교연구 - QCA에 의한 세 가지 조례 비교」. [UV] [ScienceON](https://scienceon.kisti.re.kr/srch/selectPORSrchArticle.do?cn=NART129062680)
- 윤선일·김정숙 (2022), 『지방행정연구』, on 인구조례 diffusion; 이정철·허만형 (2012), 출산장려금 EHA. [UV]

### Inferences
- Korean EHA consistently finds **vertical/national pressure**. Our "near-random within bursts" result probably reflects mandate-driven waves, e.g., ordinance changes after a national law amendment. A cheap, high-value feature: detect mandate cues in bill titles and speeches ("법 개정에 따라", "상위법", "표준조례안", "위임") and model mandate-driven and voluntary issues separately.
- The Korean literature never forecasts, never covers all 17 metropolitan councils across many issues at once, and never uses minutes text. Each of these is a legitimate differentiation claim. Phrase it as "to our knowledge," given the search limits.

### Gaps
- KCI/RISS/DBpia could not be searched exhaustively (search budget). A manual KCI check of "지방의회 회의록" with "텍스트마이닝" or "토픽" for 2022–2026 is recommended before final claims.

---

## Q5. The gap our project fills, with recommendations and framing

### Takeaway
Our combination is new as far as I could find:
1. Bottom-up issue discovery across **all 17 metropolitan councils**.
2. **Discussion-stage** tracking in **minutes**.
3. Explicit **cross-reference extraction** used both as graded evidence and as a predictive feature.
4. A **leakage-free prospective forecast** with reported AUC and top-k hit rates.
5. **Evidence-grounded narration** with verbatim quotes and no causal claims.

Each piece has precedents; the combination does not. Closest prior work:
- Gilardi, Shipan & Wüest 2021 for the discussion stage;
- Glick & Friedland 2014 and De Ruiter & Schalk 2017 for explicit references;
- Harden et al. 2023 (NEHA) and DellaVigna & Kim for hazard modeling;
- 이석환·이승모 2021 for metropolitan-level Korean EHA.

### Cited Findings
- The field is mostly retrospective and explanatory, with no AUC benchmarks found. [Connor & Clauset 2018](https://arxiv.org/abs/1810.08988); [LaCombe & Boehmke draft](https://www.scottlacombe.com/uploads/1/2/0/5/120596042/sage_pub.pdf)
- Diffusion can show up before adoption, in issue definition. [Gilardi et al. 2021](https://ideas.repec.org/a/wly/amposc/v65y2021i1p21-35.html)
- Policymakers' documents frequently discuss other states, especially neighbors and innovators. [Glick blog](https://blogs.lse.ac.uk/usappblog/2014/05/05/state-policymakers-tend-to-look-for-lessons-from-their-neighbors-and-other-innovative-states/)
- Neighbor effects are unstable and often non-significant in incomplete diffusion histories. [Mallinson & Jansa 2026](https://www.cambridge.org/core/journals/state-politics-and-policy-quarterly/article/when-is-the-right-time-to-do-a-policy-diffusion-study/0C1EE5747165B5745B46F62AE93EF058)
- Party alignment, not proximity, is the strongest recent diffusion predictor in the U.S. [DellaVigna & Kim](https://www.restud.com/wp-content/uploads/2025/08/PolicyDiffusion2025-07-21_main.pdf)
- In Korea, the 광역-jurisdiction path beats contiguity. [김진영·이석환 2016](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002190568) Party and sister-city networks matter. [이대웅·권기헌 2014](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001890336)
- National pressure drives adoption. [이정철·허만형 2016](https://cau.scholarworks.kr/handle/2019.sw.cau/8114?mode=full)
- Minutes-NLP surveys do not address cross-municipality diffusion. [Campos et al. 2026](https://arxiv.org/abs/2602.08162)
- LLM annotation can match experts when the codebook is clear. [Nakamura et al. 2026](https://arxiv.org/abs/2609.22133)

### Inferences

#### (a) Novelty assessment and closest prior work

| Component | Closest prior work | Novelty level |
|---|---|---|
| Discussion stage before adoption | Gilardi, Shipan & Wüest 2021 (newspapers, one policy, explanatory); Parinandi et al. 2021 (cosponsorship vs vote) | **Medium**: concept exists; minutes-based, multi-issue, forecasting use is new |
| Explicit cross-references as evidence/feature | Glick & Friedland 2014 (research briefs, 2 states); De Ruiter & Schalk 2017 (Dutch debates, countries) | **High**: no study found that tests references → later adoption |
| Issue discovery from bill titles + embeddings | Linder et al. 2020 / Burgess et al. 2016 (text reuse); 장석준 외 2015 (typology, 8 ordinances) | **Medium-high**: embedding clustering at 17-council scale is new for Korea |
| Out-of-sample hazard forecasting | Berry & Berry 1990 → Kreitzer & Boehmke 2016 → Harden et al. 2023 (explanatory); Connor & Clauset 2018 (forecasting, federal) | **High** for subnational adoption with reported AUC/hit-rate (none found) |
| Korean all-17-council, many-issue coverage | 이석환·이승모 2021 (one policy, 광역, Cox) | **High** |
| Evidence-graded verbatim narration, no causal claims | none found in the diffusion literature | **High** as a product feature; matches the competition rules |

**Main novelty threats to cite proactively:**
- Gilardi et al. 2021, for the conceptual "issue-definition stage";
- Loffredo & Yun 2025, for the LLM-agent diffusion proposal;
- NANET 발언 빅데이터 and the 2026 council-minutes AI DB, for infrastructure;
- the IP&M 2025 text-based diffusion-intensity paper, which needs a manual check.

#### (b) Feature/method recommendations and realistic performance targets

Features, all computed strictly from data before the forecast origin:
1. **Cumulative adoption exposure**: share and count of councils already adopting issue k, and time since first adoption (Connor & Clauset; DellaVigna & Kim's "proportion adopted").
2. **Discussion-stage intensity in the target council**: issue-k mentions in the last 3 and 6 months and acceleration (Gilardi et al.). Split into "practical/consequence" and "normative" mentions; the practical ones are the frames that respond to prior adoptions.
3. **Explicit cross-reference features**, at three levels:
   - (i) the target council cites any adopter on issue k;
   - (ii) the number of distinct councils cited;
   - (iii) the cited council's adoption is already enacted, not merely proposed.

   Also compute the lead-time distribution. Exclude same-session references attached to the bill under review to avoid leakage.
4. **Learned tie exposure** instead of contiguity. Weight prior adopters by empirical leader→follower frequencies or by title/text-reuse similarity in the training window (Desmarais et al. / Harden et al. / Linder et al.). Also test macro-region (김진영·이석환) and same-majority-party exposure (DellaVigna & Kim; 이대웅·권기헌), if in-period party data are allowed.
5. **Council innovativeness**: historical early-adopter rank from the training window (SPID).
6. **Vertical-mandate flag**: national law or 표준조례 cues in titles and speeches (이정철·허만형; Kim 2013; Garrett & Jansa's model-legislation logic). Report forecasting performance separately for mandate-driven and voluntary issues. This should explain the burst problem and protect the headline metric.
7. **Issue-type heterogeneity**: partial pooling or random slopes by instrument/theme cluster (Kreitzer & Boehmke 2016; Mallinson & Jansa 2026).

Evaluation:
- PR-AUC; Brier skill score against the base rate and against a cumulative-adopters baseline; calibrated probabilities (isotonic or Platt); reliability plot.
- Top-k hit rate and lift; per-issue mean average precision.
- Cluster bootstrap by issue.
- Ablation: base → +discussion → +cross-reference → +mandate flag.

Realistic targets. These are my judgment, not literature benchmarks, since none exist:
- AUC 0.75–0.80 on voluntary issues;
- top-3 hit rate at or above 0.35, about 4× random;
- Brier skill score > 0 after calibration;
- a significant ablation gain from cross-reference features.

Expect within-burst ordering to stay near random. Present it as a finding: "mandate waves are synchronous, so the forecast targets timing, not order."

Methodological caution: with 17 units and 24 months, every issue sits early in its diffusion life course. Pool across issues, report CIs, and avoid generalizing neighbor or party effects (Mallinson & Jansa 2026). Keep the no-causal-claims stance. Cross-references are documented attention, not proof of influence; this is consistent with the issue-definition literature.

#### (c) Wow-point framing
- **"Policy weather forecast for 17 councils"**: for each emerging issue, a ranked list of the councils most likely to adopt within 6 months, with calibrated probabilities, backtested AUC and hit rates. Prior diffusion research almost never publishes out-of-sample forecasts (Connor & Clauset: "largely retrospective").
- **"We hear it before it passes"**: discussion-stage signals in the minutes lead the ordinance. Show the median lead time from first mention to adoption, and from first explicit cross-reference to adoption, with verbatim quotes. This turns Gilardi et al.'s issue-definition stage into a working early-warning signal from policymakers' own words.
- **"Evidence ladder"**:
  - L1: adoption event (bill);
  - L2: discussion mention;
  - L3: explicit cross-reference citing another council's enacted ordinance (e.g., "경기도는 이미 제정…").

  Each flow arrow on the map is labeled with its evidence level and a quote, never with a causal verb.
- **"Who listens to whom"**: a cross-reference citation network, showing which councils are most cited (cf. De Ruiter & Schalk: larger jurisdictions are cited more) next to the adoption network. Show where the two agree and disagree. Pair it with the honest finding that geography is a weak predictor in Korea too, consistent with U.S. evidence that proximity is declining.

### Gaps
- Two benchmark claims need a manual check before final copy: "no prior AUC benchmark exists" and "no study tests references → adoption." The WebSearch budget ran out before an exhaustive sweep of 2022–2026 ACL, KDD and Korean journals.
- Check whether the competition rules allow in-period external covariates (party control, region) before using party-alignment features.
