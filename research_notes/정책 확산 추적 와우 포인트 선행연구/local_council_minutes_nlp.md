# Prior work on NLP for local council and legislative minutes, cross-council issue tracking, and Korean parliamentary/local-council NLP (gap map for the 2026 KISTI x 국회도서관 problem)

Scope note: research done 2026-10-11. "Verified" means I read the claim on the cited page or in the PDF text I extracted. Items marked **[snippet-only]** came from search-engine summaries and I did not open the source page, so the report writer should treat them as unverified. Tool budget note: the web-search quota ran out near the end, so a few follow-ups (LREC 2016 paper page, VotIE, the Linder et al. text-reuse paper, the 2025 final-results notice) could not be opened.

---

## Q1. Shared tasks and datasets on local assembly / council minutes (international). What tasks exist, and does any of them track the same issue across councils over time?

### Takeaway
Shared tasks (NTCIR QA Lab-PoliInfo 1–4) and datasets (MeetingBank, LocalView, CitiLink-Minutes, the Japanese prefectural minutes corpus) all treat minutes **within one meeting, one assembly, or one document**: segmentation, summarization, QA, stance, fact or answer verification, entity linking, budget linking, and vote extraction. None of the shared tasks or datasets I found defines a task for tracking the **same issue across councils over time** (first observation, propagation, or diffusion). Services like CivicSearch, CDP and citymeetings.nyc offer search, topic alerts and chaptering, not diffusion with evidence. Diffusion has been studied with text only for **bill or ordinance text reuse** (e.g., the Legislative Influence Detector), not for deliberation in minutes.

### Cited Findings

**NTCIR QA Lab-PoliInfo series (Japan; the closest shared-task precedent)**
- NTCIR-14 QA Lab-PoliInfo (2019) had three tasks: **Segmentation, Summarization and Classification**. It ran on Japanese political information such as local assembly minutes and newsletters. — [NTCIR-14 overview PDF](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings14/pdf/ntcir/01-NTCIR14-OV-QALAB-KimuraY.pdf)
- NTCIR-15 QA Lab-PoliInfo-2 (2020) had four subtasks: **Stance classification, Dialog summarization, Entity linking, Topic detection**. Topic detection was motivated by COVID-19: input was assembly newsflashes, output was "Lists of dialog topic words/phrases per speaker" (Tokyo Metropolitan Assembly 2020 minutes in the example). 15 teams were active. The paper reports 90 submissions in the results section and 105 in the conclusion, an internal inconsistency. — [NTCIR-15 overview PDF](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings15/pdf/ntcir/01-NTCIR15-OV-QALAB-KimuraY.pdf)
- NTCIR-16 QA Lab-PoliInfo-3 (2022) had four subtasks: **QA Alignment, Question Answering, Fact Verification, Budget Argument Mining**. Fact Verification checks "the credibility of political claims using predefined primary sources", with the Tokyo Metropolitan Assembly Minutes as the primary source and human-written newsletter summaries (都議会だより) as true claims. 11 teams were active, with 143 submissions plus 22 late ones. — [NTCIR-16 overview PDF](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings16/pdf/ntcir/01-NTCIR16-OV-QALAB-KimuraY.pdf)
- NTCIR-17 QA Lab-PoliInfo-4 (Dec 2023) had four subtasks: **Question Answering-2, Answer Verification, Stance Classification-2, Minutes-to-Budget Linking**. Answer Verification "aims to check the output of the Question Answering subtask", which is effectively fact-checking of generated answers. Stance Classification-2 was "extended … to several local governments in Japan other than Tokyo Metropolitan Assembly": training data covered 26 local governments in Saitama and testing covered 27 Saitama governments plus one hidden Fukuoka government. Explicit 賛成/反対 tokens were masked as [STANCE]. MBLink links Otaru city mayor's budget-explanation sentences to budget tables. There were 183 submissions from 8 teams. Some teams used ChatGPT, e.g., one had "ChatGPT classify" combined answer items. The paper notes that LLM summarization suffers from "hallucination". — [NTCIR-17 overview PDF](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings17/pdf/ntcir/01-NTCIR17-OV-QALAB-OgawaY.pdf)
- The underlying corpus "contains minutes from the local assemblies of 47 prefectures in Japan from April 2011 to March 2015". NTCIR-17 notes that Japanese local minutes "are difficult to access without crawling and scraping". — [NTCIR-17 overview PDF](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings17/pdf/ntcir/01-NTCIR17-OV-QALAB-OgawaY.pdf)
- I found **no PoliInfo task in NTCIR-18** (2024–25) or in the accepted **NTCIR-19** task list (conference Dec 2026), so PoliInfo-4 (NTCIR-17) appears to be the last edition. **[snippet-only]** — [NTCIR-18 page](https://research.nii.ac.jp/ntcir/ntcir-18/), [NTCIR-19 call](https://research.nii.ac.jp/ntcir/ntcir-19/Call_for_TaskProposals.html)

**Japanese local assembly minutes corpus (地方議会会議録コーパス)**
- Kimura et al. 2016, "Creating Japanese Political Corpus from Local Assembly Minutes of 47 prefectures", ALR12 @ COLING 2016. It covers prefectural assembly minutes from Apr 2011 to Mar 2015 and notes that collecting and unifying formats nationally is "cost inefficient". **[snippet-only for paper details; corpus scope confirmed in NTCIR-17 text]** — [ACL Anthology W16-5410](https://preview.aclanthology.org/fix_video/W16-5410.pdf)
- **LREC 2026**: Takamaru, Ototake, Uchida, Kimura, "Construction of Japanese Prefectural Assembly Minutes Datasets across Three Electoral Terms: Comparative Analysis of 2011, 2015, and 2019 Four-Year Periods". It covers all 47 prefectural assemblies over 2011–2023 with **12,236,974 records / 743,147,226 characters**, and links speakers to gender, age and electoral district. Its analyses are demographic and discourse-level (gender/age speech share), plus a web search and visualization system. It does not mention cross-prefecture issue propagation. — [ACL Anthology author page (Yuzu Uchida)](https://aclanthology.org/people/yuzu-uchida/)
- Akiba et al. 2024 (NLP4PoliSci @ LREC-COLING 2024), "Masking Explicit Pro-Con Expressions for Development of a Stance Classification Dataset on Assembly Minutes": 15,018 instances built automatically from 47 Japanese local governments and used in NTCIR-17 Stance Classification-2. — [ACL Anthology author page](https://aclanthology.org/people/yuzu-uchida/)

**MeetingBank (Hu et al., ACL 2023)**
- "MeetingBank: A Benchmark Dataset for Meeting Summarization" (Hu, Ganter, Deilamsalehy, Dernoncourt, Foroosh, Liu), ACL 2023, pp. 16409–16423. It covers **1,366 city council meetings from 6 major U.S. cities, 3,579 hours, 6,892 segment-level summarization instances**. The authors used a divide-and-conquer alignment of professionally written minutes to meeting segments, and the average meeting runs 2.6 h with about 28k tokens. They tested extractive, fine-tuned abstractive and GPT-3 summarizers. The task is **segment summarization only**, with no cross-city linkage. — [ACL Anthology](https://aclanthology.org/2023.acl-long.906/), [PDF](https://aclanthology.org/2023.acl-long.906.pdf)

**LocalView (Barari & Simko, Scientific Data 2023)**
- "LocalView, a database of public meetings for the study of local politics and policy-making in the United States", *Sci Data* 10:135 (2023), DOI 10.1038/s41597-023-02044-y. It contains **139,616 meeting videos with transcripts, 1,012 places, 2,861 governments, 2006–2022**, built from YouTube captions (about 90% captioned). The demonstrated uses are normalized keyword counts over time (vaccines, masking, etc. by partisan category) and salient-phrase counts (e.g., "affordable housing" 41,533). The paper does **not** analyze policy diffusion. It notes that localities that start posting tend to keep posting, which supports longitudinal study. — [PMC full text](https://pmc.ncbi.nlm.nih.gov/articles/PMC10015146/)
- MIT Center for Constructive Communication is working with the LocalView developers to apply NLP "including large language models" and build "summarization, topic modeling, and search tools". Its stated aim is to relate place-based discussions to outcomes in the same place. Diffusion is not mentioned. — [MIT CCC project page](https://www.ccc.mit.edu/project/city-meeting-transcript-analysis/)
- Barari & Simko (Publius 2025) mention policy diffusion between local governments as a possible use of meeting data, but their worked example measures national partisan phrases in local meetings. **[snippet-only]** — [Barari PDF](http://soubhikbarari.com/writings/publius24.pdf)
- Martin & Venugopal (arXiv 2604.21202, Apr 2026) transcribed city council meetings from **115 California cities** and found that "topical content varies only modestly across towns and over time". The abstract contains no diffusion analysis. — [arXiv](https://arxiv.org/abs/2604.21202)

**Other municipal-minutes datasets and systems**
- **CitiLink-Minutes** (Campos et al., ECIR 2026; arXiv 2602.12137): 120 European-Portuguese municipal minutes from 6 municipalities, >1M tokens, >38,000 annotations in three layers (metadata, subjects of discussion, voting outcomes). Its baselines cover metadata extraction, topic classification and vote labeling. The authors state that municipal records "received little attention in IR and NLP" because annotated datasets are lacking. — [arXiv](https://arxiv.org/abs/2602.12137)
- **VotIE** extracts voting events from municipal minutes and compares feature-based, fine-tuned encoders and generative LLMs, including cross-municipality generalization. **[snippet-only]** — [ResearchGate](https://www.researchgate.net/publication/399559085_VotIE_Information_Extraction_from_Meeting_Minutes)
- **Council Data Project** (Brown et al., JOSS 2021, 6(68):3904): open-source software that collects, transcribes and indexes municipal meetings (minutes, agendas, votes, video). Metadata was verified. Features and adoption counts (17 vs 19 cities, depending on source) are **[snippet-only]**, as is the claim that the research paper built a longitudinal Seattle, Portland and King County dataset with an n-gram tool. — [JOSS](https://joss.theoj.org/papers/10.21105/joss.03904)
- **CivicSearch** (Datamuse): "covers 547 cities and towns in the US and Canada", uses recent LocalView content, groups discussions into **75 frequently-discussed local policy topics**, and sends topic email alerts. The directory page does not confirm LLM summaries. — [civictech.guide listing](https://civictech.guide/listing/civicsearch)
- **citymeetings.nyc** (Vikram Oberoi, launched Feb 2024): transcribes NYC Council meetings and splits them into short, AI-generated, human-reviewed chapters. The site says "designed to enable human oversight every step of the way". Since Aug 2024 it has published within 24 h, and the NYC Charter Revision Commission contracted it in 2025. It covers a **single jurisdiction**. — [citymeetings.nyc/about](https://citymeetings.nyc/about/)

**Text-based diffusion work (bills and ordinances, not minutes)**
- **Legislative Influence Detector** (Burgess et al., KDD 2016): Smith-Waterman local alignment plus Elasticsearch over more than 500k state bills and about 2,400 model bills. It reports 45,405 bill-to-bill and 14,137 model-to-bill reuse instances. **[snippet-only]** — [DSSG LID page](https://dssgfellowship.org/lid/)
- A Policy Studies Journal article (likely Linder et al., "Text as Policy") finds that between-state text-reuse rates correlate with policy diffusion network ties. **[snippet-only; authorship not verified]** — [NSF PAR](https://par.nsf.gov/servlets/purl/10121488)

### Inferences
- In NTCIR's terms, our "evidence level" taxonomy (explicit reference / common external factor / temporal order / unknown) combines **fact verification** (PoliInfo-3) and **answer verification** (PoliInfo-4) with a new cross-document, cross-assembly **linking** problem that no PoliInfo edition defined. Citing NTCIR gives judges a recognized lineage, and the cross-council tracking is the delta.
- PoliInfo-4's Stance-2 moved toward multiple local governments, but only as a pooled classification dataset, not as tracking. "Same issue across councils over time" remains undefined as a task.
- LocalView, CivicSearch and the California study show that cross-locality **topic counting** is common. **Attributed diffusion** (who raised it first, how it moved, on what evidence) is not done in minutes. LID-style text reuse covers bills, not speech.

### Gaps
- I could not open the NTCIR-18/19 pages directly, so the absence of PoliInfo there rests on search summaries.
- I could not confirm whether any 2025–2026 ACL/EMNLP or arXiv paper defines a "cross-council issue diffusion from minutes" task. The search budget ran out before a dedicated arXiv sweep, so the report writer should flag this as "none found in a limited search".

---

## Q2. Korean resources: CLIK (지방의정포털) and Open API, 국회도서관 발언 빅데이터, AI Hub datasets, and Korean papers on 국회·지방의회 회의록 NLP

### Takeaway
Korea has strong **data infrastructure** for local-council minutes:
- **CLIK Open API**, which covers 17 광역시도 minutes, bills, members and policy info.
- **발언 빅데이터**, which segments both 국회 and 지방의회 minutes into speech units.
- AI Hub QA data for 국회 minutes.
- A new private 216k-minute local-council archive (개혁연구원, 2026).

What exists for analytics is shallow. CLIK's "지방의회 이슈키워드" shows a national top-10 keyword list with hit counts but **no cross-council comparison, trend, or AI summary**. I found no KCI/ACL paper that does NLP on 광역의회 minutes, let alone diffusion. Korean diffusion studies (조례 확산) use adoption events with event-history models, not text of deliberations.

### Cited Findings

**CLIK 국회도서관 지방의정포털**
- The portal tagline is "지방의회에 국회도서관을 더하다". It integrates 의안, 회의록, 예산·결산정보, 지방자치법규, 5분자유발언 and 지방의원현황, and links 243 councils. The portal page says 광역 16, which conflicts with the Open API page's 17. — [clik.nanet.go.kr](https://clik.nanet.go.kr/)
- **CLIK Open API**, all RESTful under clik.nanet.go.kr with key-based access and xml/json output:
  - 지방의회 회의록 (`/openapi/minutes.do`): "17개 광역시도 및 175개 기초자치단체 회의록을 조회".
  - 의안정보 (`/openapi/bill.do`) and 의원정보 (`/openapi/assemblyinfo.do`): "17개 광역시도 및 125개 기초자치단체".
  - 지방정책정보 (`/openapi/policyinfoList.do`).
  - Minutes searchType options are ALL, MTR_SJ (안건), MINTS_HTML (본문), RASMBLY_NM and PRMPST_CMIT_NM. Results sort by accuracy or meeting date.
  - Bills can be filtered by proposal-date range (itncStartDt/itncEndDt). Member search includes SPKNG_CN (발언내용).
  - There is a daily traffic limit (ERROR09).

  — [CLIK Open API guide](https://clik.nanet.go.kr/potal/guide/resourceCenter.do)
- **CLIK "지방의회 이슈키워드"** (menu linked to ARGOS): shows a top-10 keyword list such as "서울세계불꽃축제", "GTX 착공" and "한강공원". It has a 전국 default plus 17 시도 filters and year/month selectors (2025–2026). For a selected keyword it shows result counts by 의안 / 회의록 / 뉴스 (e.g., 의안 1, 회의록 47, 뉴스 0). The page has **no per-council comparison chart, no trend graph, and no AI/LLM summary**. One keyword-to-result match looked loose: a Seoul keyword returned a Busan council document. — [CLIK 이슈키워드](https://clik.nanet.go.kr/argos/index.do)

**국회도서관 발언 빅데이터 (dataset.nanet.go.kr)**
- The service describes itself as "국회·지방의회 회의록에 대한 발언자, 키워드 검색 및 다운로드, 인포그래픽 등 다양한 의정기록 데이터 서비스". On 2026-10-11 it showed **회의록 39,547건 / 발언 데이터셋 16,714,740건**. The sidebar lists 서울특별시, 부산광역시, 울산광역시 and 경상남도 council minutes, so local coverage appears partial.
- Features: Excel download of speaker datasets, top-10 keywords, word clouds, speech counts by speaker, and a 시범 extractive summarization of speeches over 500 characters. The page mentions no API. The latest data at access was the 22대 국회, 2026-10-06. — [발언 빅데이터](https://dataset.nanet.go.kr/)
- It launched in Sept 2021 with about 12M speech units from the 16th–21st 국회. **[snippet-only]** — [전자신문 2021-09-01](https://www.etnews.com/20210901000207?m=1)

**AI Hub**
- "생성형AI 국회 회의록 기반 지식 검색 데이터" (dataSetSn=71795):
  - Built 2023 from 11,827 국회 minutes into **44,033 QA pairs**: 추출형 91.82%, 단답형 8.18%. Fields are "컨텍스트 전체 원문", "학습용 컨텍스트", "생성요약 질문" and "생성요약 답변".
  - The meeting-type split is 국정감사 40.71%, 소위원회 40.91%, 특별위원회 9.96%, 예결위 5.24%, 본회의 3.17%, covering the 15th–21st 국회.
  - Opened in beta 2024-06-28, finalized 2024-10-30, with sub-labels added 2024-12-04.
  - Its suggested use is a "국회 회의록 기반의 챗봇 서비스". The reference model is KoAlpaca, with targets BLEU-2 of 20 and F1 ≥ 65.4.
  - It has **no evidence-span or retrieval labels** and **no local-council data**.

  — [AI Hub 71795](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=71795)
- AI Hub 회의 음성 data (dataSetSn=464): about 7,000 h of meeting, broadcast and UCC speech, including 의회 녹취록, with 회의록 자동 작성 및 요약 as a use case. **[snippet-only]** — [AI Hub 464](https://aihub.or.kr/aihubdata/data/view.do?dataSetSn=464)
- I found no AI Hub dataset specifically for 지방의회 회의록 summarization. **[negative result from search]**

**New 2026 actor: 개혁신당 싱크탱크 개혁연구원**
- It collected **216,561 지방의회 회의록 (1991 to Mar 2026)** and built an "AI 검색 체계". Keywords such as '주차 문제', '청년 일자리' and '노인 돌봄' return related minutes. It also has an "AI 정책 플랫폼" that scores a policy's 정강·정책 적합도 and compares it with previous local-election winners.
- The minutes are released for anyone to use ("누구나 활용할 수 있도록"), along with about 9,800 국회 minutes from 2012 onward.
- The article describes **no cross-council comparison or diffusion feature**.

  — [시대 2026-04-03](https://www.sidae.com/article/2026040314295767892)

**Korean academic NLP on minutes (KCI etc.)**
- 이현출·장재호·김경태: topic modeling of 20대 국회 보건복지위 minutes (16 topics; conflict structure by party, agenda, time, member). **[snippet-only]** — [KCI ART002604780](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002604780)
- 김정연 (2018, 미래정치연구): WORDFISH scaling of 법사위 minutes for ideological positions. **[snippet-only]** — [KCI ART002358200](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002358200)
- L(u)PIN (arXiv 2405.07320): LLM / Sentence-BERT ideology estimation for Korean 국회의원 speeches. **[snippet-only]** — [alphaxiv](https://www.alphaxiv.org/ko/abs/2405.07320)
- **Korean policy-diffusion (조례 확산) studies** use adoption events, not text:
  - 장석준·노종호·김대진 (2015, 정부학연구): leaders and diffusion patterns of 혁신 조례 by Lowi policy type, using 8 ordinances. **[snippet-only]** — [KCI ART002069217](https://www.kci.go.kr/kciportal/landing/article.kci?arti_id=ART002069217)
  - 환경조례 수평적·수직적 확산: by end-2016, 240 governments had a 환경기본조례 vs 75 with a 자연환경보전조례. **[snippet-only]** — [KCI ART002393893](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART002393893)
  - 사회적기업 조례: event-history panel logit on 56 Seoul/Gyeonggi governments, 2009–2012. 자매결연 and party networks were significant. **[snippet-only]** — [KCI ART001890336](https://www.kci.go.kr/kciportal/ci/sereArticleSearch/ciSereArtiView.kci?sereArticleSearchBean.artiId=ART001890336)
- A search for KCI papers applying topic modeling or LLMs to **광역의회 회의록** returned none. The closest work used 국회 committee minutes, 서울시 민원, or 17 광역 data-administration plans. **[negative result; limited search]**

### Inferences
- The CLIK Open API is the most important reusable asset. It makes our pipeline **reproducible and deployable** on the 국회도서관's own infrastructure, which is a strong argument for NAL judges. The 2026 sample file name "2025_서울특별시의회_sample.json" suggests the organizers distribute per-council-year JSON, likely derived from CLIK (inference).
- CLIK's current 이슈키워드 is exactly the "before" picture we can improve. It shows "what is hot nationally this month" but not where an issue started, where it moved, or why. Our system can be pitched as **"이슈키워드 2.0: 출처·경로·근거가 있는 이슈 흐름"**.
- 개혁연구원's 216k-minute AI search is a **novelty threat for plain local-minutes RAG/search**, and it is public and recent. It reinforces that a minutes RAG chatbot is no longer novel in Korea. It does not do diffusion or evidence grading.
- Korean 조례 확산 literature gives theory (수평/수직 확산, 인접효과, 정당·자매결연 네트워크). Our evidence levels can operationalize it: "common external factor" ≈ 수직적 확산 (central law or policy), and "explicit reference" ≈ 학습/모방 by citation of another council. Citing this literature signals social-science grounding.

### Gaps
- CLIK Open API full terms (redistribution, rate limits, key approval time) are not stated on the guide page.
- I could not verify how many 광역의회 are covered in 발언 빅데이터. The sidebar lists only a few.
- I could not find whether CLIK/ARGOS 이슈키워드 is generated by an algorithm or curated. The argos.nanet.go.kr page returned empty content.

---

## Q3. Prior KISTI DATA·AI 분석 경진대회 problems and winners tied to the National Assembly Library or minutes

### Takeaway
The 국회도서관 has posed a minutes problem almost every year:
- **2023**: 국회회의록 요약 모델 개발.
- **2024**: 국회 회의록 기반 의정활동 지원 및 대국민 알권리 보장 챗봇 서비스.
- **2026**: 광역 지방의회 회의록 기반 지방정책 이슈 트랜드 분석 및 흐름 예측.

Past winners were a **local-LLM summarizer (2023)**, a **local Advanced-RAG chatbot over 국회 minutes (2024)**, and in 2025 a **news/SNS "입법 수요 레이더" dashboard with bill matching** (우수상).

**Correction to the brief:** the "의정활동 지원 및 대국민 알권리 보장 챗봇" problem was the **2024** problem, not 2025. I found no 국회도서관-proposed problem in 2025. NAL was a co-host and gave 국회도서관장상 as one of four 우수상.

Judges' feedback visible in the 2025 deck centred on **quantitative quality, index stability, matching precision, and data governance**.

### Cited Findings

**2023**
- Problem "국회회의록 요약 모델 개발", proposed by **국회도서관 데이터융합분석과**, 2023 DATA·AI 분석 경진대회. Applications ran 2023-07-10 to 07-28. — [AIDA PROB_209](https://aida.kisti.re.kr/competition/main/problem/PROB_000000000000209/detail.do)
- 2023 장려상: "LLM을 활용한 국회회의록 요약 모델". Overview: "Large Language Model을 사용하여 국회회의록의 특징을 고려한 요약문 생성". DOI 10.23057/79. — [AIDA entry](https://aida.kisti.re.kr/data/49f23e07-900c-47b9-9c4d-cd3329972bca)
- A related "Ksum" deck on AIDA, of uncertain year or award (Korean glyphs did not extract), compares **LongT5 (0.3B)** with **LLaMA2-Chat 7B + LoRA**. LoRA trainable parameters were 79,953,920 of 6,935,810,048 (1.15%), with int8 quantization on 4×A6000. BERTScore with KcELECTRA was **0.7611 (LLaMA2) vs 0.5289 (LongT5)**, and GPT-3.5 was used to generate training data. **[partially verified; text partly unreadable]** — [Ksum deck PDF](https://aida.kisti.re.kr/data/fc951635-3580-4a07-bd5b-20ac910419b9/6fadf02c-9f2a-4532-9b3a-675e488289e3/01.%E1%84%87%E1%85%A1%E1%86%AF%E1%84%91%E1%85%AD%E1%84%8C%E1%85%A1%E1%84%85%E1%85%AD.pdf)

**2024**
- Problem "국회 회의록 기반 의정활동 지원 및 대국민 알권리 보장 챗봇 서비스", "(정책지정) 국회도서관", prize "국회도서관장상 상금 200만원". Applications ran 2024-08-23 to 10-25 and a sample zip of about 36 MB was provided. — [AIDA PROB_401](https://aida.kisti.re.kr/competition/main/problem/PROB_000000000000401/detail.do), [2024 competition page](https://aida.kisti.re.kr/competition/main/competition/COMP_000000000000030/detail.do)
- 2024 **우수문제해결상**: "API 비용과 데이터 유출 걱정 없는 Advanced RAG 기반 국회 회의록 챗봇", subtitle "국회 회의록 요약 챗봇 서비스". Publisher 강병하, DOI 10.23057/157, posted 2025-03-14, 31,349 views. — [AIDA entry](https://aida.kisti.re.kr/data/f2fd831e-a8e6-45ef-a726-fe8f2890c25b)
- What the 2024 winner's deck shows (extracted text):
  - Training/validation counts by meeting type: 33,416 / 4,188, covering 국정감사, 본회의, 소위원회, 예결특위 and 특위 from the 15th–21st 국회.
  - LLM-generated synthetic questions for two personas (국민 and 국회의원).
  - Embedding selected via the Kor-IR benchmark. A **fine-tuned multilingual-e5-large-instruct** beat OpenAI text-embedding-3-large and Upstage embeddings at @150: NDCG 0.5865 vs 0.5118 / 0.5829, Recall 0.7146 vs 0.6825 / 0.7066.
  - Adding **bge-reranker-v2-m3** raised NDCG@10 from 0.5657 to 0.5771. The deck cites "Lost in the Middle".
  - Demo prompts include "최저임금 인상과 관련하여 국회에서 논의된 내용을 시간순으로 요약해줘", and outputs include time-ordered summaries and a list of major historical issues.

  — [2024 winner deck PDF](https://aida.kisti.re.kr/data/a9759b84-2937-4405-974d-c398d5d8b02b/d9b1515f-af30-41ab-b760-9196562afae8/%EB%B0%9C%ED%91%9C%EC%9E%90%EB%A3%8C.pdf)
- In the same deck, a demo answer on "홍명보 감독 … 임명 과정" assembles a "시간순 진행 과정" from 2017-10-13, 2017-10-30, 2018-10-10 and 2019-10-28 hearings. It appends linking sentences such as "이는 감독 선임 과정에서도 … 강조합니다" to hearings about other matters (KFA governance, player selection, senior appointments). — [2024 winner deck PDF](https://aida.kisti.re.kr/data/a9759b84-2937-4405-974d-c398d5d8b02b/d9b1515f-af30-41ab-b760-9196562afae8/%EB%B0%9C%ED%91%9C%EC%9E%90%EB%A3%8C.pdf)

**2025**
- KISTI's 2025 call names only two of seven problem titles (콘크리트 점검; 지하수위 예측). 국회도서관 appears as co-host and as the giver of 국회도서관장상, one of four 우수상 at 100만원. 대상 was 국회의장상, 400만원. Documents were evaluated 10-20 to 24 and awards given on 12-03. — [KISTI news 6742](https://www.kisti.re.kr/promote/post/news/6742)
- 2025 **우수상**: "여론·입법 연계 분석 대시보드", subtitle "소셜 미디어 트렌드 분석을 통한 입법 수요 지수 도출 및 법안 매칭 프레임워크와 시각화 대시보드". Publisher 한윤지, DOI 10.23057/144, posted 2025-12-31. — [AIDA entry](https://aida.kisti.re.kr/model/e45619a0-00ce-4a51-bbdf-16f29ea75773)
- Its deck is titled **"뉴스·소셜 기반 AI 입법 수요 레이더: 실시간–주간–월간 다층 분석과 법안 정밀 매핑"**, by team **One&Only**, dated 2025-10-30. Contents:
  - **Pipeline**: Naver/Kakao/YouTube collection → TF-IDF+K-means (default) or SBERT+BERTopic → LDI score → bill matching via local CSV then 국회 OpenAPI → domain guard (penalty for topic–bill mismatch) → weekly/monthly reports and draft 입법제안서(안).
  - **LDI formula**: "LDI = 문서 수(45%) + 확산(30%) + 감정 절대값(15%) + 뉴스 비율(10%)", where 확산 = platform weight × time decay.
  - **Self-positioning**: the solution is "not a tool that turns opinion into law". It looks for "법적 공백·개정 필요".
  - **Reported metrics**: P@3 0.75, DCR (domain consistency) 0.625, Coverage 0.75, "해당없음" 0.25.
  - **Section "종합 의견에 대한 대응"** (response to judges' overall comments): topic quality (silhouette 0.031→0.066), LDI stability (Spearman ρ = 0.06 between Sept and Oct, 6 common topics), matching evidence (label CSV + evaluate_kpi.py), and governance (API terms, PII removal via sanitize_pii.py).

  — [2025 winner deck PDF](https://aida.kisti.re.kr/data/216e4d6b-44e1-40fc-a1d6-6a37a6616e8b/d609c91f-ef96-4b42-aa44-14341a3fd6a2/%EB%B0%9C%ED%91%9C%EC%9E%90%EB%A3%8C.pdf)
- A "2025 최종 결과 공지" notice dated 2025-12-05 exists, but its content could not be opened (JS link). — [AIDA notices](https://aida.kisti.re.kr/competition/main/notice.do)

**2026 (our competition)**
- Problem "광역 지방의회 회의록 기반 지방정책 이슈 트랜드 분석 및 흐름 예측", proposed by 국회도서관. Applications run 2026-09-15 to 11-06, and the sample file is "2025_서울특별시의회_sample.json" (about 45.5 KB). Full data and the problem description were not visible publicly. — [AIDA PROB_4600](https://aida.kisti.re.kr/competition/main/problem/PROB_000000000004600/detail.do)
- Schedule: submissions close 11-06, 서류평가 runs 11-09 to 13, and 최종 발표평가 and the award ceremony are on **11-25 at KISTI 대전본원 키움관**. Problem-solving awards are 대상 국회의장상 300만원, 최우수 과학기술부총리상 200만원, and 100만원 each for **국회도서관장상**, 대전시장상, 해양경찰청장상, 한국수자원공사사장상 and 대전중구청장상. Excellent winners also get a conference presentation and "후속 공동연구 참여 기회". — [충청뉴스 2026-09-16](http://www.ccnnews.co.kr/news/articleView.html?idxno=415045)
- Evaluation tables on the overview page:
  - (A) 적절성 50 / 효과성 50.
  - (B) **창의성 20 / 우수성 50 / 효과성 30**.
  - The page does not label which table belongs to which track. Rules require copyright-cleared data and tools, and winners are published via DataON or AIDA.
  - The overview page does **not** mention a ban on generative AI or commercial APIs. The brief's "commercial APIs forbidden" constraint is not visible on public pages and may be in the problem description or 참가신청서.

  — [AIDA overview](https://aida.kisti.re.kr/competition/main/overview.do)
- A Q&A thread titled "생성형 AI 활용 관련 문의" exists on the 2026 site. — [AIDA main](https://aida.kisti.re.kr/competition/main/main.do)
- Earlier NLP winners on AIDA include "자연어처리 기술을 활용한 여론 분석모델 (2022년 경진대회 최우수상)". **[snippet-only]** — [AIDA](https://aida.kisti.re.kr/data/c5c111e1-6715-4467-92e4-437180bc5b81)

### Inferences
- **What judges have already rewarded:** summarization with local LLMs (2023), a local RAG chatbot with retrieval metrics (2024), and trend detection with an index, matching and a dashboard (2025). A "minutes RAG chatbot" and a "trend dashboard with an index" are therefore both **already-seen genres**. Our novelty must come from **cross-council flow attribution with graded evidence** and **verified narratives**, not from RAG or keyword trends per se.
- The 2024 winner made **"no API cost, no data leakage"** (local models) its headline. Since 2026 effectively requires local models (per brief), that is now table stakes, not a differentiator.
- The 2025 deck's "종합 의견에 대한 대응" reveals what judges probed: **clustering quality, index stability over time, precision of matching, and governance (PII, API terms)**. Expect the same questions for our diffusion edges and forecasts. Prepare precision/recall on a labeled edge set, temporal backtest stability, calibration, and a PII/copyright note.
- The 홍명보 demo (2024 deck) is a concrete example of the failure our evidence levels address. A temporally ordered retrieval stitched into a causal-sounding narrative is what our taxonomy would label "시간적 선후 only / 근거 불충분" instead of asserting a link. This is our inference from the deck text, and it should be presented respectfully, e.g., as "generic RAG risk", without naming the team.
- The 2025 LDI stability of ρ = 0.06 shows how hard month-to-month issue identity is. Our issue-identity (cross-time, cross-council clustering) needs explicit stability evaluation.

### Gaps
- I could not open the 2025 final-results notice or confirm which team received the 국회도서관장상 in 2025, so I cannot say whether the One&Only entry won that specific prize.
- I could not identify the 2024 winner's generator LLM or answer-quality evaluation. Slide bullets are images.
- The 2026 full problem statement, data spec (17 councils, 2024–2025) and API rule are not public on AIDA without login. They rest on the participant's brief.

---

## Q4. National Assembly Library AI initiatives (NAIL / 국회AI도서관) that our output could plug into

### Takeaway
The NAL is building "국회AI도서관" under the **내일(NAIL: National Assembly AI Library) 프로젝트**. The plan is to unify scattered AI services into an **AI agent system**, with an explicit goal of **proactively providing legislative inspiration to members (입법 영감 선제 제공)**. NAIL SEARCH (pilot, March 2026) and the chatbot 사서 나비 are live. A cross-council issue-flow tracker that emits evidence-graded "issue cards" fits the "proactive provision" philosophy and could be one tool or agent inside NAIL. CLIK is the natural data and UI host.

### Cited Findings
- Director 황정근 (interview conducted 2026-02-09, published 2026-02-13):
  - Plans to train AI on a full-text database of "915만 건, 4억 5000만 면" toward "국회AI 도서관", via the "내일(NAIL: National Assembly AI Library) 프로젝트".
  - Goal of "AI 에이전트 체계 구축" that answers questions like "탄소중립 정책 추진의 주요 쟁점은".
  - Philosophy: "국회도서관은 '수집'만 잘하는 게 아니라 '제공'을 제대로 해야 합니다", i.e., proactively give legislative ideas before members ask. Examples are '금주의 월드로' and '금주의 보고서'. The interview mentions "지역구별 이슈 분석".
  - Copyright limits mean only 30–40% of the content can be opened to the public.

  — [천지일보 2026-02-13](https://www.newscj.com/news/articleView.html?idxno=3374965)
- **NAIL SEARCH** (natural-language search returning summaries, keywords and suggestions) piloted on about 1M full-text items from the last 5 years, out of 13.78M holdings, with staged expansion during 2026. 사서 나비 added book and policy-material recommendations. The 국가전략포털 added AI summary/translation (2024) and AI Q&A for think-tank reports. The quoted goal is "지능형 지식허브로 도약하는 첫걸음". The article does **not** mention 회의록, 지방의회 or CLIK. — [더페어 2026-03-17](https://www.thefairnews.co.kr/news/articleView.html?idxno=71695)
- A target to finish AX by 2030, the need for an ISP and GPU budget first, and an "integrated AI agent" so users need not move between portals. **[snippet-only]** — [더팩트 interview](https://news.tf.co.kr/read/ptoday/2304662.htm), [fn 이사람](https://v.daum.net/v/20260225183742927)

### Inferences
- "입법 영감 선제 제공" maps directly onto **diffusion forecasting**: "This issue started in council X and has spread to Y and Z with explicit references, so your council or region is likely next (p = …), and here are the verified precedents." That is proactive provision, not reactive search.
- NAIL's integration goal suggests delivering our system as a **callable tool with structured JSON outputs** (issue card, flow graph, evidence level, verified narrative), not just a dashboard. This reads as "plugs into the NAIL agent" to NAL judges.
- NAIL news coverage does not mention local-council minutes, so a local-council analytics agent fills a visible hole in the NAL AI portfolio. This is an inference from the absence of any mention in two articles.

### Gaps
- I found no official NAL roadmap document, only interviews and news. The 2030 target, ISP and GPU budget details are from search snippets.
- It is unknown whether NAIL will expose APIs or a tool interface for third-party modules.

---

## Q5. What clear gap remains, and how should we frame differentiation and the wow-point for 국회도서관 and KISTI judges?

### Takeaway
The open gap is the combination of (i) **issue identity across councils and time** from deliberative minutes, (ii) **first-observation and directed flow with graded, auditable evidence** (explicit reference / common external factor / temporal order / unknown), (iii) **forecasting of diffusion** validated by temporal backtesting, and (iv) **narratives whose every claim is verified and labeled by evidence level**, all on local open models. Each piece has partial precedents in separate communities:
- NTCIR verification tasks.
- LID-style text reuse.
- 조례 확산 event-history studies.
- LocalView topic counts.
- RAG chatbots.

No system or shared task found here integrates them for council minutes, in Korean or elsewhere.

### Cited Findings
- Shared tasks on local minutes stop at within-assembly QA, stance, verification, summarization and linking. — [NTCIR-17](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings17/pdf/ntcir/01-NTCIR17-OV-QALAB-OgawaY.pdf), [NTCIR-16](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings16/pdf/ntcir/01-NTCIR16-OV-QALAB-KimuraY.pdf), [NTCIR-15](https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings15/pdf/ntcir/01-NTCIR15-OV-QALAB-KimuraY.pdf)
- Large cross-locality corpora are used for counts, topics and participation, not diffusion. — [LocalView](https://pmc.ncbi.nlm.nih.gov/articles/PMC10015146/), [California 115 cities](https://arxiv.org/abs/2604.21202), [CivicSearch](https://civictech.guide/listing/civicsearch)
- Korea's official issue view (CLIK 이슈키워드) is a top-10 keyword list with hit counts, with no cross-council comparison or AI summary. — [CLIK 이슈키워드](https://clik.nanet.go.kr/argos/index.do)
- Prior KISTI x NAL winners are a summarizer, a RAG chatbot and an SNS-trend dashboard. — [2024 winner](https://aida.kisti.re.kr/data/f2fd831e-a8e6-45ef-a726-fe8f2890c25b), [2025 winner](https://aida.kisti.re.kr/model/e45619a0-00ce-4a51-bbdf-16f29ea75773)
- NAL's leadership explicitly wants proactive provision and an agent system. — [천지일보](https://www.newscj.com/news/articleView.html?idxno=3374965)

### Inferences

#### (a) Gap assessment

| Capability | International precedent | Korean precedent | Status for our project |
|---|---|---|---|
| Minutes search / RAG chatbot | CDP, citymeetings.nyc, CivicSearch | 2024 KISTI winner; 개혁연구원 216k-minute AI search; NAIL SEARCH | **Saturated**. Do not lead with it. |
| Summarization | MeetingBank; PoliInfo summarization | 2023 KISTI 장려상 (LLM); 발언 빅데이터 extractive pilot | Saturated |
| Topic or keyword trends | LocalView counts; CivicSearch 75 topics | CLIK 이슈키워드 top-10; 2025 KISTI LDI dashboard | **Seen**. Needed as a base layer only. |
| Stance / fact / answer verification | NTCIR PoliInfo-2/3/4 | None found for local councils | Reusable idea; new for Korean local minutes |
| Cross-jurisdiction diffusion via text | LID (bill text reuse); PSJ text-reuse | 조례 확산 studies (adoption events, no text) | **Not done on minutes**. Core novelty. |
| First observation + directed flow with evidence grades | None found | None found | **Core novelty** |
| Diffusion forecasting from deliberation | None found (adoption-based EHA only) | EHA on ordinance adoption | **Novel in this data modality** |
| Claim-level verified narrative with evidence labels | Generic RAG faithfulness work; NTCIR Answer Verification | None found for minutes | **Novel combination; the trust angle** |

Caveat: "none found" reflects a limited search. Phrase it in the submission as "to our knowledge".

#### (b) Concrete differentiation suggestions
1. **Define the task formally, NTCIR-style.** Name it, e.g., "Cross-Council Issue Flow Attribution (CCIFA)". Specify inputs, outputs and metrics:
   - Issue clustering purity and stability across months. The 2025 judges probed exactly this, and the 2025 winner reported ρ = 0.06.
   - First-observation accuracy.
   - Edge precision/recall per evidence level.
   - Forecast AUC/Brier score with calibration.

   Ship a **small gold set**, e.g., 100–200 council-pair edges with double annotation and Cohen's κ. This mirrors how PoliInfo built tasks and signals "research capability" to KISTI.
2. **Make "explicit reference" a high-precision extractor.** Detect speech acts that cite other councils or regions ("서울시의회는 이미 ○○ 조례를 제정", "타 시도 사례", "경기도처럼"). This is the deliberation analogue of LID's text reuse and gives the strongest edges. Report its precision separately.
3. **Model "common external factor" explicitly (vertical diffusion).** Align spikes with national triggers: 국회 bill or law changes via 국회 OpenAPI, central-government announcements, and news events. Edges explained by a shared shock should be **down-graded** from "diffusion" to "co-response". Cite the Korean 수평적/수직적 확산 literature to show theory grounding.
4. **Treat "temporal order" as a weak label and say so.** UI and narrative must never upgrade it to causation. Show a mini case study where generic RAG produces a causal-sounding timeline from temporally ordered but unrelated records, and your verifier labels it "시간적 선후만 확인". Frame it as a generic RAG risk.
5. **Claim-level verification for narratives.** Decompose generated text into atomic claims, attach minute spans (council, date, speaker, page or line), and run an NLI or local-LLM judge. Show a per-claim badge (명시적 인용 / 공통 외부요인 / 시간 선후 / 근거 불명) and **abstain** when support is missing. Report supported-claim rate, citation precision/recall, and a human-audited sample. Cite NTCIR-16 Fact Verification and NTCIR-17 Answer Verification as precedents for "verifying generated answers against minutes".
6. **Backtest forecasting honestly.** Train on 2024 and predict 2025 adoption or mention by councils not yet discussing an issue. Report lead time (months of early warning) and calibration plots. Use bills and ordinances (CLIK `/openapi/bill.do`, proposal-date filters) as **outcome labels**, so forecasts link to concrete legislative action, not just talk.
7. **Add a stance and coalition layer (optional).** Per-council 찬반 on the same issue, reusing the NTCIR Stance Classification idea with masked explicit tokens, shows not just spread but **contestation**.
8. **Ensure deployability for NAL.**
   - Build on the CLIK Open API (17 광역 minutes, bills, members).
   - Output JSON "issue cards" and a flow graph that an agent can call. Name the integration target "NAIL agent tool / CLIK 이슈키워드 확장".
   - Report runtime and hardware for local models and a PII/copyright statement. Judges asked the 2025 winner about governance.
9. **Use reproducibility as a KISTI signal.** Plan to publish code, a model card and the gold set via AIDA with a DOI, as prior winners did with DOIs 10.23057/79, /144 and /157.

#### (c) Wow-point framing for these judges
- **One-line pitch (KO):** "검색하는 챗봇이 아니라, 지방정책 이슈가 *어디서 처음 나와 어떤 근거로 어디로 번지는지*를 증거 등급과 함께 보여주고, 다음 확산지를 미리 알려주는 '국회AI도서관용 선제적 이슈 레이더'."
- **For 국회도서관 judges:**
  - Show the CLIK 이슈키워드 page (today: top-10 keywords with counts), then the same issue as a **cross-council flow map with first-observer, evidence-graded edges, and a verified narrative**. Frame it as "이슈키워드 2.0".
  - Tie it explicitly to the director's stated goals: "입법 영감 선제 제공" and "AI 에이전트 체계 (NAIL)".
  - Mention that the input is the NAL's own CLIK Open API, so it is deployable in-house on local models without data leaving the 국회.
- **For KISTI judges:**
  - Present a defined task, a gold set with inter-annotator agreement, ablations (e.g., without the external-factor control, how many "diffusion" edges are really co-responses), temporal backtests with calibration, and faithfulness metrics for generated narratives.
  - This answers the 우수성 (50 pts) and 창의성 (20 pts) criteria with evidence, not demos.
- **Trust narrative:**
  - "Every sentence the system writes carries a source span and an evidence level, and the system says '모름' when the minutes do not support a link."
  - Contrast with generic RAG timelines that over-link temporally adjacent records.
  - This positions the entry as **trustworthy generative AI for public institutions**, beyond "local LLM = no leakage", which was already the 2024 winner's headline.
- **Lineage slide:** NTCIR PoliInfo (JP, 2019–2023) → MeetingBank / LocalView (US, 2023) → CitiLink (PT, 2026) → **this work (KR, 2026): the first cross-council issue-flow attribution with verified narratives on Korean 광역의회 minutes (to our knowledge)**.

### Gaps
- Novelty claims rest on a limited search. A dedicated arXiv/ACL 2025–2026 sweep for "policy diffusion + meeting transcripts/minutes + LLM" and for Korean 지방의회 회의록 NLP on RISS/DBpia could not be completed after the search quota ran out.
- I could not verify whether the 2026 organizers will provide reference labels (e.g., known diffusion cases) or expect a specific forecast target. This should be checked in the full problem description.
