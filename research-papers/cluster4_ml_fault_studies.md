# Cluster 4: DER Placement in ML/Simulation-Based Fault Detection, Classification, and Location Studies

**Prepared for:** Undergraduate thesis — "Machine Learning–Based Fault Zone Identification in DER-Integrated Distribution Feeders Under Sparse and Degraded Sensor Conditions"
**Target system:** EPRI Ckt7 in OpenDSS, Random Forest + SVM, voltage/current/smart-meter outage features, SLG/LL/3-phase faults, 0% and 50% DER penetration
**Report date:** 2025

---

## Table of Contents
1. [Source 1 — Ensemble Voting + Smart Meters (INL/FAMU-FSU, 2022)](#source-1)
2. [Source 2 — SVM Fault Location with DGs at Specified Buses (ISGT 2013)](#source-2)
3. [Source 3 — SVM Fault Location with Micro-PMU on IEEE 11-node (Sensors 2022)](#source-3)
4. [Source 4 — ML Adaptive Fault Diagnosis with Hosting Capacity Amendment (EPSR 2023)](#source-4)
5. [Source 5 — RF Embedded in Smart Meter for Fault Detection (SEGN 2023)](#source-5)
6. [Source 6 — Data-Driven Fault Localization with DER on IEEE-123 (Energies 2020)](#source-6)
7. [Source 7 — Physics-Informed GNN Fault Location, OpenDSS (IEEE Trans. 2021)](#source-7)
8. [Source 8 — XGBoost Fault Localization via OpenDSS with High DER Penetration (KIEE 2025)](#source-8)
9. [Source 9 — IBDER Modeling for Protection, EPRI J1 Feeder, OpenDSS (NREL/IEEE 2022)](#source-9)
10. [Source 10 — ML Fault Detection on 25 kV Feeder with High DG Penetration (IEEE 2024)](#source-10)
11. [Synthesis: How Comparable Papers Handle DER Placement — and the Gap the User Fills](#synthesis)

---

## Source 1 — Ensemble Voting Classifier + Smart Meters on IEEE-123 with PV Microgrid {#source-1}

**Full Citation:**
M. Dabbaghjamanesh, S. Karabiber, E. E. Farsangi, and M. Jafari, "Ensemble Voting-Based Fault Classification and Location Identification for a Distribution System with Microgrids Using Smart Meter Measurements," *IET Smart Grid / Wiley–INL Technical Report*, Idaho National Laboratory, October 2022. DOI: Available via INL Digital Library. URL: https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_63727.pdf

**ML Method:**
Ensemble Voting Classifier (EVC) combining three base learners: Random Forest (RF, 100 trees), k-Nearest Neighbors (kNN, k=3, Euclidean), and Artificial Neural Network (ANN, 3 hidden layers × 90 neurons). Both hard and soft voting tested. Scikit-learn implementation.

**Test Feeder / Simulation Tool:**
- Feeder: Modified IEEE-123 bus distribution test feeder (128 buses, 4.16 kV), extended to include PV-based microgrid.
- Simulation tools: **OpenDSS** (offline, frequency-domain, data generation via Python–COM interface) + OPAL-RT digital real-time simulator (hardware-in-the-loop validation) + Simulink/Simscape for transient implementation.
- **[OpenDSS] FLAG**

**DER Placement Approach:**
PV units placed at **five specific named buses**: Bus 300 (350 kW), Bus 151 (500 kW), Bus 56 (500 kW), Bus 450 (350 kW), and Bus 95 (350 kW). These buses were selected because they correspond to the open-switch tie points of the modified IEEE-123 feeder that define the microgrid islanding zones — i.e., placement was chosen to align with the network's switching topology, not by any optimization method. Total PV capacity ≈ 2,050 kW; no single system-wide penetration percentage is stated. Smart meters (43 total, at branch ends and PV plants) served as the primary measurement infrastructure. **[Placement arbitrary / topology-aligned]** — the paper provides no hosted-capacity or optimization citation for the bus selection; bus choice is justified only by the observation that these buses serve as microgrid boundary points.

**Key Findings:**
- 100% classification accuracy for SLG, LL, and 3-phase faults within 15 Ω fault resistance; accuracy degrades slightly above 15 Ω for double-line-to-ground faults.
- Fault location identification accuracy: 97.65% (SLG), 97.80% (3-phase) using hard voting.
- Event-driven smart meter voltage data (threshold trigger at <0.95 or >1.05 pu) dramatically reduces communication bandwidth vs. high-rate PMU approaches, while maintaining robustness to 10% Gaussian noise and 25% data loss.

**Application Note:**
This is the most directly comparable paper to the user's work: it uses OpenDSS for simulation, RF as a core classifier, smart-meter voltage data as features, and explicitly tests SLG/LL/3-phase faults across multiple penetration scenarios. The user can cite this paper as the baseline smart-meter-plus-ensemble approach and contrast it by noting that (a) the IEEE-123 feeder is well-studied whereas EPRI Ckt7 is a utility-derived, heterogeneous radial feeder with more complex topology, and (b) DER buses were chosen to match switching topology rather than via a replicable placement methodology — a gap the user fills by explicitly comparing 0% and 50% DER penetration with placement documented relative to Ckt7 load buses. The user can also argue that sparse/degraded sensor conditions (absent in this paper) represent an additional gap addressed by the thesis.

**Flags:** [OpenDSS] [RF/SVM] [Placement arbitrary / topology-aligned]

---

## Source 2 — Multi-Class SVM Fault Location on Practical Indian Feeder with DGs at End of Laterals {#source-2}

**Full Citation:**
A. Srivastava and S. Parida, "Identification of Fault Location in Power Distribution System with Penetration of Distributed Generations," *IEEE PES ISGT*, 2013, pp. 1–6. DOI: 10.1109/ISGT.2013.6497862. URL: https://eecs.wsu.edu/~bakken/IEEE-PES-ISGT-2013/files/ISGT2013-000264.PDF

**ML Method:**
Multi-class SVM classifier (SVM-C, one-against-one method, RBF kernel) for faulted line and fault type identification; ε-SVR (Support Vector Regression) for fault location and impedance estimation. LIBSVM library. Grid-search optimization on C and γ.

**Test Feeder / Simulation Tool:**
- Feeder: Practical distribution feeder (132/11 kV, 21 lines, 2.2 MVA total load) from a grid substation in India.
- Simulation tool: Short-circuit analysis program from IISc, Bangalore; LIBSVM for ML.

**DER Placement Approach:**
Three DGs placed at **specific named buses at the ends of laterals and at mid-lateral points**: DG1 at Bus 20 (0.6 MW), DG2 at Bus 21 (0.25 MW), DG3 at Bus 22 (0.35 MW); total DG = 1.2 MW at 60% penetration of total load. The paper explicitly states DGs are placed "at the end of laterals and in between laterals" — a conventional choice motivated by the observation that such locations allow the protection algorithm to use voltage/current measurements at all source nodes (substation + DG connection points) as inputs to the classifier. No citation to a hosting capacity or optimal placement framework is provided. **[Placement arbitrary / conventional lateral-end placement, verbally justified]**

**Key Findings:**
- Configuration with 3 DGs: 100% SVM classification accuracy; accuracy drops to 92.06% with only 1 DG, illustrating that DG measurement points are critical features.
- The approach simultaneously identifies faulted line section, fault type, fault impedance, and fault distance.
- Fault type test set includes SLG, LL, LLG, 3-phase — exact same set as the user's thesis.

**Application Note:**
This IEEE ISGT paper is directly citable as an early SVM baseline for the same fault type set (SLG, LL, 3-phase). The user can note that the DG placement follows the "end-of-lateral" convention without optimization citations, and that the practical Indian feeder and IISc simulation tool are not reproducible/standard public benchmarks. By contrast, EPRI Ckt7 in OpenDSS provides a documented, publicly available feeder, and the user's 50% penetration scenario extends beyond the 60% single-scenario tested here with a systematic before/after comparison. The 2013 date also signals a gap in methodological evolution toward modern simulation-based data generation.

**Flags:** [RF/SVM] [Placement arbitrary — lateral-end convention, no optimization cited]

---

## Source 3 — SVM Fault Section Detection on IEEE 11-Node with Three DGs at Fixed Buses {#source-3}

**Full Citation:**
H. Mirshekali, R. Dashti, A. Keshavarz, and H. R. Shaker, "Machine Learning-Based Fault Location for Smart Distribution Networks Equipped with Micro-PMU," *Sensors*, vol. 22, no. 3, p. 945, Jan. 2022. DOI: 10.3390/s22030945. URL: https://www.mdpi.com/1424-8220/22/3/945

**ML Method:**
SVM classifier (linear kernel) with Neighborhood Component Feature Selection (NCFS) for dimensionality reduction; frequency-domain features (FFT of voltage α-components at 5 kHz). Compared against KNN baseline.

**Test Feeder / Simulation Tool:**
- Feeder: IEEE 11-node standard distribution test feeder.
- Simulation tool: MATLAB/Simulink 2020b.

**DER Placement Approach:**
Three DGs placed at **specific fixed nodes**: DG1 at Node 9 (4 MVA, X/R=5), DG2 at Node 10 (8 MVA), DG3 at Node 11 (6 MVA). Total DG capacity: 18 MVA. Nodes 9, 10, and 11 are terminal/end nodes of the 11-node feeder — essentially the far-end nodes of the main lateral. The placement is determined by the structure of the standard test case (which comes with DG locations embedded), not by any optimization. Four micro-PMUs are placed at nodes 1, 9, 10, and 11 — i.e., at the DG buses. The paper does not provide any citation for why DGs are at these nodes nor a penetration percentage. **[Placement inherited from standard test case — effectively arbitrary]**

**Key Findings:**
- SVM achieves 97.87% accuracy for SLG fault section identification using only voltage signals (no current); KNN achieves 93.93%.
- The method is not sensitive to fault impedance and works without protection relay information.
- Micro-PMU data with 5 kHz sampling supports frequency feature extraction that captures DG-induced fault current signatures.

**Application Note:**
The user can cite this paper as evidence that SVM performs well for fault section identification in DG-equipped networks using only voltage features. However, the user's work goes further by incorporating current features and smart-meter outage data, and by using EPRI Ckt7 — a far larger and more complex feeder than the 11-node benchmark. Importantly, DG placement in this paper is implicitly inherited from the test case definition; the user can explicitly contrast this by stating that in the EPRI Ckt7 study, DER placement at 50% penetration was assigned systematically at load buses with proportional capacity to avoid bias, documenting what this paper fails to specify. This distinction directly supports a research-gap claim.

**Flags:** [RF/SVM] [Placement arbitrary — inherited from standard test case, no justification cited]

---

## Source 4 — Histogram Gradient Boost for Fault Diagnosis with Hosting Capacity Amendment, IEEE-33 {#source-4}

**Full Citation:**
S. K. Sahu, M. Roy, S. Dutta, D. Ghosh, and D. K. Mohanta, "Machine Learning Based Adaptive Fault Diagnosis Considering Hosting Capacity Amendment in Active Distribution Network," *Electric Power Systems Research*, vol. 216, p. 109025, Mar. 2023. DOI: 10.1016/j.epsr.2022.109025. URL: https://www.sciencedirect.com/science/article/abs/pii/S0378779622010744

**ML Method:**
Histogram-based Gradient Boost (HGB) algorithm for fault type detection and localization; spectral-kurtosis for feature extraction. The model is retrained when the network's hosting capacity changes — an adaptive/online learning framework.

**Test Feeder / Simulation Tool:**
- Feeder: Reconfigured IEEE-33 bus distribution system.
- Simulation tool: Typhoon HIL real-time simulator.

**DER Placement Approach:**
The paper is framed around changes in DER hosting capacity — i.e., the system parameter altered is the *amount* of DER that can be safely accommodated, not the placement of individual units. From the abstract and summary descriptions, specific DER bus locations and placement methodology are not publicly stated (full text behind paywall). The key contribution is that when hosting capacity increases (more DER is added), network parameters change and the ML model must be retrained. This implicitly acknowledges that DER *amount* affects fault signatures but does not methodologically address DER *location*. **[Placement undisclosed / hosting-capacity framework, no placement justification available]**

**Key Findings:**
- Adaptive ML retraining approach addresses the degradation in fault classification accuracy when the DER mix changes (hosting capacity amendment).
- The HGB algorithm outperforms prior published methods in comparative tests on the IEEE-33 bus system.
- Spectral-kurtosis enables noise-robust feature extraction for transient fault signals.

**Application Note:**
This paper is uniquely citable because it directly acknowledges that DER integration (hosting capacity changes) forces ML model retraining — providing theoretical support for why the user's decision to explicitly test 0% vs. 50% penetration levels with separate trained classifiers is methodologically sound. The user can cite this to motivate the two-penetration-level design. However, the paper provides no guidance on *where* DER is placed, only how much. This is precisely the gap the user's work addresses: the user specifies placement methodology on Ckt7 (e.g., proportional to load, at specific node types), which this paper leaves open.

**Flags:** [RF/SVM-adjacent — gradient boost] [Placement undisclosed]

---

## Source 5 — Random Forest Embedded in Smart Meter for Fault Detection, IEEE 13-Node {#source-5}

**Full Citation:**
S. Dutta, S. K. Sahu, M. Roy, and S. Dutta, "A Data Driven Fault Detection Approach with an Ensemble Classifier Based Smart Meter in Modern Distribution System," *Sustainable Energy, Grids and Networks*, vol. 34, p. 101012, Jun. 2023. DOI: 10.1016/j.segan.2023.101012. URL: https://www.sciencedirect.com/science/article/abs/pii/S2352467723000206

**ML Method:**
Random Forest (RF) classifier embedded within the smart meter hardware/software environment. Feature: magnitude of the maximum angular difference between positive and zero sequence components of the three-phase current at the DG bus. 500 simulated fault cases covering 10 fault types.

**Test Feeder / Simulation Tool:**
- Feeder: IEEE 13-node distribution network (highly loaded, short feeder, 50 Hz).
- Simulation tool: MATLAB/Simulink (referenced as "SIMINK" in the text).

**DER Placement Approach:**
A single DG is connected at **Bus 1** (the source/substation-end bus) of the IEEE 13-node network. The smart meter is also located at the DG bus. The paper describes a simplified 3-bus conceptual model (DG bus = Bus 1, load bus = Bus 2, PCC/grid bus = Bus 3). No justification is provided for the choice of Bus 1 as the DG location; it appears to be a simplification to demonstrate the embedded smart-meter algorithm in a single-DG scenario. No penetration percentage is given. **[Placement arbitrary — single DG at source bus, no citation or justification provided]**

**Key Findings:**
- RF embedded in the smart meter achieves 98.95% fault detection accuracy across 10 fault types.
- The algorithm eliminates the need for separate hardware/software for fault detection, enhancing situational awareness at low cost.
- The approach transmits fault signals to neighboring smart meters and the utility, supporting distributed situational awareness.

**Application Note:**
This paper is directly relevant to the user's inclusion of smart-meter outage features. The user can cite it to motivate embedding fault intelligence in AMI infrastructure and to validate the RF classifier as the appropriate choice for smart-meter-based detection. However, the paper tests a single DG at one bus on a 13-node feeder — far simpler than EPRI Ckt7 with distributed PV at 50% penetration. The user can argue that extending this smart-meter + RF approach to a large, heterogeneous EPRI feeder with spatially distributed DER and sparse sensor coverage is a direct contribution not addressed by this work.

**Flags:** [RF/SVM] [Placement arbitrary — single DG at source bus, no justification] [Smart Meter/AMI]

---

## Source 6 — Data-Driven Fault Localization with 50% DER Penetration, Random Placement, IEEE-123 {#source-6}

**Full Citation:**
Z. Lin, D. Duan, Q. Yang, X. Hong, X. Cheng, L. Yang, and S. Cui, "Data-Driven Fault Localization in Distribution Systems with Distributed Energy Resources," *Energies*, vol. 13, no. 1, p. 275, Jan. 2020. DOI: 10.3390/en13010275. URL: https://www.mdpi.com/1996-1073/13/1/275

**ML Method:**
Support Vector Data Description (SVDD, one-class SVM variant) combined with Kernel Density Estimation (KDE/p-values) for confidence-level fault localization. Multi-level system regionalization using tree segmentation. Features include voltage, current, apparent/active/reactive power (1,278-dimensional feature vector for the full system).

**Test Feeder / Simulation Tool:**
- Feeder: IEEE-123 node test feeder.
- Simulation tool: GridLAB-D.

**DER Placement Approach:**
DER units placed at **randomly generated locations** on the feeder. Generation level outputs uniformly distributed from 80%–120% of a pre-defined generation level. Total penetration: **50%** (total DER capacity = 50% of total feeder load). This is the most explicit statement of random DER placement found in the surveyed literature — and there is **no citation or methodological justification** given for the random placement decision. The paper acknowledges that traditional protection suffers 12 mal-operations at 50% DER vs. 4 mal-operations at 0%, validating the impact of DER on fault localization. **[Placement explicitly random — stated but not justified]**

**Key Findings:**
- Data-driven SVDD strategy achieves 92.57% localization accuracy at 50% DER penetration, compared to traditional relay-based methods that suffer significant mal-operation.
- Traditional overcurrent protection has 12 relay operations for a single fault at 50% penetration (vs. 4 at 0%) — quantifying the protection challenge of DER integration.
- The p-value comparison across subregions provides a principled confidence measure for fault localization that traditional methods lack.

**Application Note:**
This is one of very few surveyed papers that explicitly state their DER penetration level (50%) AND mention random DER placement. The user can directly compare to this paper: both study 50% penetration, but this paper uses random placement without justification on IEEE-123/GridLAB-D while the user applies a documented placement on EPRI Ckt7/OpenDSS. The user can argue: "Random DER placement as in [Lin et al., 2020] creates uncontrolled variation in training data characteristics; our study assigns DER proportionally to load at documented bus IDs, enabling reproducibility." This is a clear methodological gap the user fills and can be framed as a contribution.

**Flags:** [RF/SVM-adjacent — SVDD] [Placement explicitly random, no citation or justification] [Placement arbitrary]

---

## Source 7 — Physics-Informed GNN Fault Location on IEEE-123/37, OpenDSS {#source-7}

**Full Citation:**
W. Li, D. Deka, "Physics-Informed Graph Learning for Robust Fault Location in Distribution Systems," *arXiv preprint* arXiv:2107.02275, submitted to IEEE Transactions on Smart Grid / Power Delivery, Jul. 2021. URL: https://arxiv.org/pdf/2107.02275v1.pdf (Note: also published/presented in IEEE proceedings; confirm full journal citation.)

**ML Method:**
Two-stage physics-informed Graph Neural Network (GNN): Stage I uses an adjustable-adjacency GNN for graph embedding; Stage II uses GNN label propagation with statistical similarity-based adjacency. Baselines include CNN, fully-connected NN, and Graph Convolutional Network (GCN). Features: three-phase voltage signals at sparse measurement nodes.

**Test Feeder / Simulation Tool:**
- Feeders: IEEE 123-node (128 buses, 21 measurement nodes) and IEEE 37-node (36 nodes, 15 measurement nodes).
- Simulation tool: **OpenDSS**. — **[OpenDSS] FLAG**

**DER Placement Approach:**
DER placement details are **not stated** in the paper. The load variations follow probabilistic distributions from OpenDSS loadshape database (expectation 0.53 p.u.) to simulate operating condition variability. Fault scenarios include SPG, PP, and DPG faults at all three-phase nodes with impedance 0.05–20 Ω. No DER penetration level is explicitly stated. **[Placement not discussed — DER integration not a focus of the paper]**

**Key Findings:**
- With only 15–21 measurement nodes (sparse coverage), the GNN achieves F1 = 97.6% on the 123-node system at 15% label rate, significantly outperforming CNN, NN, and GCN baselines.
- Robust to out-of-distribution load variations and topology changes (switch reconfigurations).
- The 1-hop accuracy (LAR1-hop) stays near 100%, meaning misclassified faults are never far from the true location — important for practical dispatch.

**Application Note:**
This paper establishes that **sparse sensor coverage** is a recognized research challenge: with only 15–21 meters on large systems, physics-informed ML approaches are needed. The user can cite this as motivation for the sparse-and-degraded sensor scenario in the thesis. However, this paper does not address DER penetration as a variable, making it a gap the user fills. The OpenDSS simulation tool alignment is directly citable as methodological precedent. The user can argue that the sparse-sensor framing in this paper motivates the AMI-based sparse coverage scenario in the thesis.

**Flags:** [OpenDSS] [Placement not discussed — DER integration absent from study design]

---

## Source 8 — XGBoost Fault Localization via OpenDSS with High DER Penetration (KIEE 2025) {#source-8}

**Full Citation:**
S.-H. Lee, Y. Jeon, D. Gwon, and Y. Choi, "Machine Learning Enhances Fault Localization in Network Distribution Systems," in *Proc. KIEE Power Engineering and Energy Technology (PEET) Conf.*, Seoul, Korea, 2025. DOI: 10.1109/PEET65412.2025.11340960. URL: https://ieeexplore.ieee.org/document/11340960/

**ML Method:**
XGBoost algorithm for fault location prediction. Features: line current, FIE (Fault Indication Equipment) status, load, distributed generation output, and fault resistance. Dataset constructed from **OpenDSS simulation** reflecting diverse operating conditions.

**Test Feeder / Simulation Tool:**
- Feeder: Meshed distribution test system (Korea-specific network with loop topology, switches, and distributed generators).
- Simulation tool: **OpenDSS**. — **[OpenDSS] FLAG**

**DER Placement Approach:**
The paper describes a meshed distribution system with **distributed generators and dynamic loads** incorporated into the OpenDSS model. DER buses are described structurally as nodes that cause fault current dispersion in loop configurations ("fault current is dispersed, causing FIE failure at downstream junctions"). No explicit statement of DER bus selection methodology (random, optimal, or uniform), and no penetration percentage is stated. The implicit placement reflects the Korean distribution grid structure modeled. **[Placement arbitrary / network-specific, not methodologically described]**

**Key Findings:**
- ML model achieves average Precision 0.98, Recall 0.97, F1 0.97 across four representative fault scenarios including high-impedance faults and high DER output conditions.
- The ML approach corrects cases where conventional FIE-based detection fails due to dispersed fault current at DER buses.
- Four case study scenarios: normal fault, high DER output, load peak, and high-impedance fault — demonstrating robustness.

**Application Note:**
This is the most recent (2025) and methodologically closest OpenDSS-based paper found. The user can cite it as direct methodological precedent for using OpenDSS to generate ML training data under DER-integrated conditions. The user should note that this Korean paper uses a meshed network (not a radial feeder like Ckt7), XGBoost rather than RF/SVM, and does not describe a systematic DER placement methodology — gaps the user addresses. The user's comparison of 0% vs. 50% DER penetration is a cleaner experimental design than this paper's single-condition DER model.

**Flags:** [OpenDSS] [Placement arbitrary / network-inherited, not justified]

---

## Source 9 — IBDER Modeling for Protection Analysis on EPRI J1 Feeder in OpenDSS {#source-9}

**Full Citation:**
K. Prabakar, K. Schneider, M. Baggu, R. Jain, and Y. Velaga, "Modeling Distributed Energy Resources for Analyzing Distribution System Protection," *NREL Technical Report* NREL/TP-5D00-82331, National Renewable Energy Laboratory, Oct. 2022. DOI: 10.2172/1898413. URL: https://docs.nrel.gov/docs/fy22osti/82331.pdf

**ML Method:**
This is a protection analysis/modeling paper, not an ML paper. It uses phasor-domain simulation in OpenDSS to study relay behavior at high IBDER penetration. Included because: (a) it uses an **EPRI feeder** (J1) in **OpenDSS** — the highest priority combination for the user's context, and (b) it establishes the quantitative impact of DER placement density on relay pickup, directly informing why DER placement methodology matters. — **[EPRI feeder] [OpenDSS] FLAGS**

**Test Feeder / Simulation Tool:**
- Feeder: **EPRI J1 feeder** (12.47 kV nominal). — **[EPRI feeder] HIGHEST PRIORITY FLAG**
- Simulation tool: **OpenDSS** (phasor-domain IBDER model); validated against PSCAD/EMTDC (EMT simulation).

**DER Placement Approach:**
Twelve PV/IBDER units (PV1–PV12) **distributed across the J1 feeder** as shown in the topology figure (Figure 5 of the report). Ratings vary from 300–500 kVA (with PV1 at 4 MVA acting as a large anchor DER). Total installed capacity: 9.2 MVA at **80% penetration** (peak load 11.6 MW). The placement strategy is described as "distributed across the feeder" — matching a realistic utility deployment scenario — but there is no explicit statement of a hosting capacity analysis, optimization algorithm, or random sampling methodology. Relay locations R1–R7 were chosen based on fault current analysis and protection zone requirements. **[Placement utility-distributed, no formal methodology cited]**

**Key Findings:**
- At 80% IBDER penetration, relay R7 fails to pick up under all tested fault impedances (0.5–4 Ω) because IBDER fault currents are limited to 1.25–2.25 p.u. of rated current.
- The phasor-domain OpenDSS model closely replicates the detailed PSCAD EMT model, validating OpenDSS as a sufficient simulation platform for DER-fault studies.
- IEEE 1547-2018 momentary cessation (within 5 cycles at V < 0.5 pu) can affect backup relay coordination — a critical finding for protection researchers.

**Application Note:**
This is the highest-priority citation for the user's methodology section. The user can directly cite this paper to: (1) validate OpenDSS as the appropriate simulation tool for IBDER-fault studies (the paper validates OpenDSS against PSCAD), (2) confirm that EPRI feeders are appropriate platforms for DER-fault research (the J1 feeder is a sister feeder to Ckt7), and (3) quantify why DER penetration level affects fault classification — the user can argue that the relay failure at 80% penetration documented here motivates studying 50% vs. 0% scenarios before reaching failure thresholds. The lack of explicit DER placement methodology in this paper (despite using an EPRI feeder in OpenDSS) highlights the gap the thesis fills.

**Flags:** [EPRI feeder — J1] [OpenDSS] [Placement distributed/utility-modeled, no formal methodology]

---

## Source 10 — SVM + KNN on 25 kV Feeder with High DG Penetration (IEEE CONCAPAN 2024) {#source-10}

**Full Citation:**
A. Mejía-Dubón, D. Gutiérrez-Umaña, A. Dávila-Velásquez, and O. Núñez-Mata, "Machine Learning Techniques for Fault Detection in Simulated Synchrophasors Data 25kV Distribution Feeder," in *Proc. IEEE CONCAPAN*, Panama City, Panama, Nov. 2024. DOI: 10.1109/CONCAPAN63470.2024.10933599. URL: https://ieeexplore.ieee.org/document/10933599/

**ML Method:**
SVM and K-Nearest Neighbors (KNN) applied to voltage and current phasor data from two PMUs installed at Nodes 10 and 14. SVM/KNN used for binary and multi-class classification of phase-to-ground (SLG) faults.

**Test Feeder / Simulation Tool:**
- Feeder: 25 kV distribution feeder with **high load** and **substantial penetration of Distributed Generation (DG)** — a utility-scale feeder modeled with PMU deployment.
- Simulation tool: OPAL-RT HYPERSIM platform (IEEE C37.118 synchrophasor data).

**DER Placement Approach:**
PMUs are **strategically placed at Nodes 10 and 14** to capture high-resolution phasor data. DG placement details are described as producing "substantial penetration" — the paper does not specify the DG bus locations, capacity, or how placement was determined. The word "substantial" (no percentage) and the absence of any placement methodology is characteristic of the broader literature. No optimization or site-selection framework is cited. **[Placement arbitrary — location and methodology undisclosed]**

**Key Findings:**
- ML methods show potential to surpass traditional protective schemes in fault classification accuracy under DG-rich conditions.
- PMU-based phasor data (synchronized at IEEE C37.118 standards) provides richer fault signatures than substation-only measurements.
- The comparison with traditional protection highlights the classification advantage of data-driven approaches.

**Application Note:**
This recent (2024) paper demonstrates continued use of SVM for distribution fault classification with DG, supporting the user's choice of SVM as a classifier. The user can note that OPAL-RT HYPERSIM with PMU data is a high-cost approach compared to OpenDSS + smart-meter simulation, and that the user's work achieves comparable fault type coverage (SLG, LL, 3-phase) using freely available EPRI Ckt7 data in OpenDSS under sparse sensor conditions. The paper's opacity about DG placement provides a specific example to cite in the user's claim that DER placement decisions are systematically underdescribed in comparable literature.

**Flags:** [RF/SVM] [Placement arbitrary — undisclosed]

---

## Synthesis: How Comparable Papers Handle DER Placement — and the Gap the User Fills {#synthesis}

Across the ten sources surveyed spanning 2013–2025, a consistent and notable pattern emerges: **no ML-based fault classification or fault location paper that integrates DER into a distribution feeder simulation provides a methodologically justified or cited DER placement strategy.** DER locations are variously inherited from standard test case definitions (Sources 3, 7), chosen to align with the network's switching topology (Source 1), placed at the ends of laterals by convention (Source 2), selected from a single-DG simplified configuration (Source 5), described as "distributed across the feeder" without a reference (Source 9), or explicitly stated as random without justification (Source 6). Only Source 6 (Lin et al., 2020) explicitly uses the word "random" for DER placement, but provides no citation — no paper invokes hosting capacity analysis (HCA), optimal DER siting algorithms, or photovoltaic interconnection screening criteria to justify bus selection. Source 4 (Sahu et al., 2023) acknowledges that changing hosting capacity forces ML model retraining, which indirectly validates the user's two-scenario (0%/50%) design but still does not specify how DER is placed. The only paper to use an EPRI feeder (Source 9, EPRI J1 in OpenDSS) describes DER as distributed across the feeder in a manner "reflecting utility deployment" — a reasonable but undocumented rationale that the user can contrast with a reproducible, documented bus-selection approach for Ckt7. This gap is significant: the absence of placement methodology means that findings in the literature cannot be fully reproduced or compared across studies, because classifier performance is sensitive to where DER units inject bidirectional power relative to the fault location and the sparse measurement nodes. The user's thesis fills this gap by explicitly documenting DER placement on EPRI Ckt7 at 50% penetration (relative to load buses, with stated node IDs and per-unit capacities), validating the chosen placement against the 0% baseline, and using OpenDSS — the native simulation environment of the Ckt7 feeder — to generate training data, thereby producing a reproducible benchmark that comparable papers lack.

---

## Quick Reference: DER Placement Decisions Across Sources

| # | Paper (Year) | Feeder | Simulation Tool | ML Method | DER Placement | Penetration | Placement Justified? |
|---|---|---|---|---|---|---|---|
| 1 | INL Ensemble (2022) | IEEE-123 mod. | OpenDSS + OPAL-RT | RF + kNN + ANN | Specific buses (microgrid tie-points) | ~2 MW / not stated | No — topology aligned |
| 2 | ISGT SVM (2013) | Indian 21-line | IISc SC program | SVM | End of laterals, named buses | 60% | No — conventional only |
| 3 | Sensors SVM (2022) | IEEE 11-node | MATLAB Simulink | SVM | End-nodes (9,10,11) inherited | Not stated | No — test case inherited |
| 4 | EPSR HGB (2023) | IEEE-33 bus | Typhoon HIL | Hist. Gradient Boost | Not disclosed | Not stated | Not disclosed |
| 5 | SEGN RF (2023) | IEEE 13-node | MATLAB Simulink | RF | Single DG at Bus 1 | Not stated | No — simplification only |
| 6 | Energies SVDD (2020) | IEEE-123 | GridLAB-D | SVDD + KDE | **Random** (explicitly stated) | **50%** | **No — no citation** |
| 7 | arXiv GNN (2021) | IEEE 123/37 | **OpenDSS** | GNN | Not discussed | Not stated | — |
| 8 | KIEE XGBoost (2025) | Korean mesh | **OpenDSS** | XGBoost | Network-inherited | Not stated | No — grid-specific |
| 9 | NREL/EPRI J1 (2022) | **EPRI J1** | **OpenDSS** | N/A (protection sim) | Distributed across feeder | **80%** | No — utility model only |
| 10 | CONCAPAN SVM (2024) | 25 kV utility | OPAL-RT | SVM + KNN | Not disclosed | "Substantial" | Not disclosed |

**User's thesis:** EPRI Ckt7 | OpenDSS | RF + SVM | Documented placement at load buses | 0% and 50% | **YES — explicit methodology**

---

*Report compiled from: IEEE Xplore, OSTI, arXiv, MDPI, INL Digital Library, NREL Technical Reports. All searches conducted via Perplexity academic and web search, June 2025.*
