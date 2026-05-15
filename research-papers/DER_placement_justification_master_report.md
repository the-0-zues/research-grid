# DER Placement Justification — Master Research Report

**Prepared for:** Theodore Lodge
**Paper:** *Machine Learning–Based Fault Zone Identification in DER-Integrated Distribution Feeders Under Sparse and Degraded Sensor Conditions*
**Simulation environment:** EPRI Ckt7 in OpenDSS; Random Forest + SVM; SLG, LL, 3-phase faults; 0% and 50% DER penetration
**Compiled:** May 14, 2026

---

## 1. Executive Overview

This report consolidates **47 sources** across five research streams to answer one reviewer-facing question:

> *"Is your DER placement at 50% penetration on EPRI Ckt7 methodologically grounded, or is it arbitrary?"*

The literature shows that this question has a defensible, layered answer drawn from four bodies of work — hosting capacity assessment (HCA), optimal DER placement and sizing, DER penetration impact studies, and ML-based fault studies — anchored by the IEEE 1547 standards family. Critically, **Cluster 4 reveals a genuine research gap**: none of the ten ML fault classification papers surveyed provides a cited, reproducible DER placement methodology. Most either inherit DER locations from a test case, use a single DG at a convenience bus, place DER at "the end of laterals" by convention, or — in only one case — explicitly state "random" placement without citation ([Lin et al., 2020](https://www.mdpi.com/1996-1073/13/1/275)). Your paper can therefore make placement methodology itself a contribution, not just a setup choice.

### Highest-leverage flagged sources

| Priority | Source | Why it matters |
|---|---|---|
| ★★★ | **Coogan, Reno & Grijalva, 2013 (Sandia)** | Uses **EPRI Ckt7 directly in OpenDSS**; quantifies HC at 50% feeder load; same feeder, same tool as your study ([OSTI 1107705](https://www.osti.gov/servlets/purl/1107705)) |
| ★★★ | **EPRI DRIVE TR-3002020018, 2019** + **EPRI TR-1026640, 2012** | The streamlined and stochastic HCA methodologies for EPRI test circuits in OpenDSS; explicitly include protection criteria |
| ★★★ | **IEEE Std 1547.7-2013** | Formal study framework — 50% penetration definitionally exceeds screening thresholds, triggering mandatory steady-state and protection impact studies |
| ★★★ | **PNNL-32230, McDermott et al., 2021** | Demonstrates conventional TOC protection fails at ~50–75% IBR penetration on EPRI J1; validates CNN zonal classification — closest methodological precedent to your paper |
| ★★ | **Prabakar et al., NREL/TP-5D00-82331, 2022** | IBDER protection modeling on **EPRI J1 in OpenDSS**, validated against PSCAD — authorizes your phasor-domain OpenDSS approach |
| ★★ | **Krishnamoorthy, Sadnan & Dubey, 2019** | Shows **50% is a structural inflection point** in power flow on EPRI Ckt-24 in OpenDSS — quantitative justification for your 50% scenario |
| ★★ | **Guzmán et al., IEEE TPWRS, 2024** | Deterministic iterative HCA with **explicit short-circuit/protection constraints** in OpenDSS — directly fuses HCA with your fault classification framing |
| ★★ | **Acharya, Mahat & Mithulananthan, 2006** + **Hung & Mithulananthan, IEEE TIE, 2013** | The canonical loss-sensitivity-factor (LSF) analytical method — defensible, lightweight bus-screening method for Ckt7 |

---

## 2. Recommended Citation Stack (use this in your "Simulation Setup" section)

Your DER placement justification should be built as a three-layer argument, with citations from this report supporting each layer:

### Layer A — *Why* DER placement methodology matters (frame the problem)
- DER placement, not just total penetration, governs fault current redistribution and protection coordination ([Almoola, Ahmed & Gatsis, 2025](https://ieeexplore.ieee.org/document/10906986/); [Alcala-Gonzalez et al., 2021](https://www.mdpi.com/2076-3417/11/1/405); [Bouchikhi et al., 2025](https://www.nature.com/articles/s41598-025-98012-0)).
- Most ML fault classification papers do not document DER placement methodology, creating a reproducibility gap ([Lin et al., 2020](https://www.mdpi.com/1996-1073/13/1/275); cross-survey of 10 papers in Cluster 4).

### Layer B — *How* you placed DER (the methodology itself)
- **Step 1 — Bus screening via Loss Sensitivity Factor on a base-case OpenDSS power flow** ([Acharya, Mahat & Mithulananthan, 2006](https://linkinghub.elsevier.com/retrieve/pii/S0142061506000652); [Elkholy, 2024](https://ieeexplore.ieee.org/document/10850009/)).
- **Step 2 — Stochastic / streamlined HCA screen at candidate buses** ([Rylander & Smith, EPRI TR-1026640, 2012]; [EPRI DRIVE TR-3002020018, 2019]; [Dubey & Santoso, IEEE TPWRS, 2017](https://doi.org/10.1109/TPWRS.2016.2622286); [Ding & Mather, IEEE TSTE, 2017](https://doi.org/10.1109/TSTE.2016.2640239)).
- **Step 3 — Iterative incremental sizing with short-circuit/protection constraints** ([Guzmán et al., IEEE TPWRS, 2024](https://doi.org/10.1109/TPWRS.2023.3326859)).
- **Step 4 — Zone-aware distribution check** so each fault zone hosts DER ([Dharmasena, Olowu & Sarwat, IEEE Access, 2022](https://ieeexplore.ieee.org/document/9720991/); [Hung & Mithulananthan, IEEE TIE, 2013](http://ieeexplore.ieee.org/document/5709978/)).

### Layer C — *Why 50% specifically* (the penetration choice)
- 50% is one of EPRI's five canonical penetration scenario boundaries ([Rylander & Smith, EPRI, 2012]).
- 50% is the structural inflection point of net power flow direction on EPRI Ckt-24 in OpenDSS ([Krishnamoorthy, Sadnan & Dubey, 2019](https://doi.org/10.1109/NAPS46351.2019.9000281)).
- 50% is the documented onset region for protection desensitization, sympathetic tripping, and PCI degradation ([McDermott et al., PNNL-32230, 2021](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-32230.pdf); [Alcala-Gonzalez et al., 2021](https://www.mdpi.com/2076-3417/11/1/405); [Vargas, Batista & Yang, 2023](https://doi.org/10.3390/en16073130)).
- 50% definitionally exceeds the IEEE 1547.7-2013 / FERC SGIP screening thresholds, triggering full impact-study scope ([IEEE Std 1547.7-2013]; [NREL FY15-63157](https://docs.nrel.gov/docs/fy15osti/63157.pdf)).

---

## 3. Ready-to-Paste Simulation-Setup Paragraph

Drop this directly into your "Simulation Setup" or "Methodology" section and trim citations to match your bibliography conventions:

> *DER placement on the EPRI Ckt7 feeder at 50% aggregate penetration was justified through a four-stage methodology that combines hosting capacity analysis, optimal placement theory, and IEEE-standard impact-study requirements. First, candidate buses were pre-screened by computing the Loss Sensitivity Factor \( \mathrm{LSF}_i = \partial P_{\mathrm{loss}}/\partial P_i \) from a base-case no-DER OpenDSS power flow at peak load [Acharya, Mahat & Mithulananthan, 2006; Hung & Mithulananthan, 2013]. Second, the LSF-ranked candidates were filtered through a stochastic / streamlined hosting capacity screen following the EPRI DRIVE methodology [Rylander & Smith, 2012; EPRI TR-3002020018, 2019], retaining only buses with positive voltage headroom (Region A/B per Rylander et al., 2015) and adequate short-circuit capacity [Dubey & Santoso, 2017]. Third, DER units were added incrementally using the exact-loss-formula sizing of Hung & Mithulananthan (2013) and the iterative protection-aware procedure of Guzmán et al. (2024), with relay-reach and sympathetic-trip checks at each increment, until cumulative installed capacity reached 50% of Ckt7 peak load. Fourth, a zone-aware distribution check confirmed that DER were dispersed across the near-substation, mid-feeder, and lateral zones of Ckt7 [Dharmasena, Olowu & Sarwat, 2022], ensuring that the resulting fault current redistribution under 50% penetration produces zone-differentiated signatures usable by the ML classifier. DER units were sized as inverter-based resources contributing 1.1–1.2× rated fault current per IEEE Std 1547-2018 Category B requirements [EPRI TR-3002013381, 2018; McDermott et al., PNNL-32230, 2021], and the 50% penetration scenario was selected because it (i) is one of EPRI's five canonical penetration scenarios [Rylander & Smith, 2012], (ii) corresponds to the structural inflection in net power flow direction documented on EPRI Ckt-24 in OpenDSS [Krishnamoorthy et al., 2019] and to the thermal/voltage stress onset documented on EPRI Ckt7 itself in OpenDSS at 50% feeder load [Coogan, Reno & Grijalva, 2013], (iii) is the documented onset region for protection desensitization and PCI degradation [Alcala-Gonzalez et al., 2021; Vargas, Batista & Yang, 2023], and (iv) definitionally exceeds the screening thresholds of IEEE Std 1547.7-2013, formally triggering steady-state and protection impact studies.*

---

## 4. Cluster Summaries

The five companion files contain full per-source entries with citation, methodology, test feeder, key findings, application note, and flag tags.

### Cluster 1 — Hosting Capacity Assessment Methods (`cluster1_hosting_capacity.md`, 10 sources)
Covers stochastic/Monte Carlo (Rylander & Smith 2012; Dubey & Santoso 2017; Ding & Mather 2017; Mašić et al. 2024), deterministic/iterative with protection constraints (Guzmán et al. 2024), streamlined EPRI DRIVE (TR-3002020018, 2019; Rylander et al. 2015), OPF-based (Silva et al. 2024 on EPRI Ckt5; Mavalizadeh & Almassalkhi 2024), and multi-site iterative (Guddanti et al. 2024). **8 of 10 are OpenDSS-based; 5 of 10 use EPRI test circuits; 5 of 10 incorporate protection/fault criteria.**

### Cluster 2 — Optimal DER Placement and Sizing (`cluster2_optimal_placement.md`, 12 sources)
Covers analytical loss-sensitivity (Acharya 2006; Hung & Mithulananthan 2013), metaheuristics (Al Soudi et al. 2026 PSO; Bouchikhi et al. 2025 GWO with protection), sensitivity-based OPF (Das et al. 2023), OpenDSS co-simulation (Elkholy 2024; Pham et al. 2022 on IEEE 123-bus; Guerra & Martinez-Velasco 2018 on **EPRI J1**), multi-objective with hosting capacity and resilience (Dharmasena et al. 2022), fault-current parametric studies (Alcala-Gonzalez et al. 2021), and the EPRI J1 voltage-reactive-power method (Dalal et al. 2023). **The synthesis defines a three-stage LSF → exact-loss sizing → zone-aware workflow directly applicable to Ckt7.**

### Cluster 3 — DER Penetration Impacts (`cluster3_penetration_impacts.md`, 10 sources)
Voltage rise and reverse power flow indices (Hasheminamin et al. 2015; Ferdowsi et al. 2020); the foundational PNNL high-PV protection report ([McDermott et al., PNNL-32230, 2021](https://www.pnnl.gov/main/publications/external/technical_reports/PNNL-32230.pdf)) with CNN zonal classification on EPRI J1; IBR short-circuit estimation (Vargas et al. 2023); CNN protection-zone classification (Ramesh et al. 2024); sympathetic tripping mitigation (Almoola, Ahmed & Gatsis 2025); the **direct EPRI Ckt7 in OpenDSS** hosting capacity study (Coogan, Reno & Grijalva 2013); the **EPRI Ckt-24 in OpenDSS** 50% inflection study (Krishnamoorthy et al. 2019); the EPRI 40-feeder stochastic baseline (Rylander & Smith 2012); and a 50% benchmark on IEEE 34-bus (Ahsan et al. 2021). **This cluster provides the quantitative justification for the 50% penetration choice.**

### Cluster 4 — DER Placement in ML/Simulation Fault Studies (`cluster4_ml_fault_studies.md`, 10 sources)
Surveys how comparable ML fault-detection papers handled DER placement. **The dominant finding: zero of the ten papers cited a placement methodology.** Approaches range from microgrid-tie-point alignment (INL Ensemble 2022), end-of-laterals convention (ISGT SVM 2013), inherited test-case nodes (Sensors SVM 2022), single-DG at source bus (SEGN RF 2023), undisclosed (EPSR HGB 2023; CONCAPAN SVM 2024), and an explicit "random" placement without citation (Lin et al. 2020 — the only paper that names its strategy but does not justify it). The NREL/EPRI J1 report (Prabakar et al. 2022) places 12 PV units across the J1 feeder but describes this only as "reflecting utility deployment." **Your placement methodology section directly fills this gap and can be framed as a contribution.**

### Cluster 5 — IEEE Standards Layer (`cluster5_ieee_standards.md`, 6 standards)
- **IEEE Std 1547-2018** (+ 1547a-2020): Category A/B voltage regulation, Categories I/II/III ride-through, reactive power minimums, anti-islanding 2-s requirement. Validated in OpenDSS via NREL's OpenDER model.
- **IEEE Std 1547.1-2020**: Five test types; Reference Point of Applicability; ES DER four-level anti-islanding.
- **IEEE Std 1547.2-2008 / 1547.2-2023**: Application guidance for AGIR category assignment, reclosing coordination, TOV limitation.
- **IEEE Std 1547.7-2013** *(Critical)*: Three-tier study methodology; five study types (screening, steady-state, transient/dynamic, protection/communication/control, other). **50% penetration definitionally exceeds the 15% peak-load and 100% min-daytime-load SGIP screens, triggering Tier 2/3 studies.**
- **IEEE Std 1547.9-2022**: ES DER-specific; Operational SoC and capacity definitions; relevant only if you include BESS.
- **IEEE Std 2030.7/2030.8**: Microgrid controller standards — cite only if Ckt7 DER are MEMS-coordinated.

---

## 5. Triple-Flagged Sources (OpenDSS + Protection/Fault + EPRI Feeder)

These are the highest-value citations because they simultaneously match your tool, your fault-classification framing, and your test circuit family:

| Source | Cluster | Why triple-flagged |
|---|---|---|
| EPRI DRIVE TR-3002020018 (2019) + Rylander et al. EPRI 2015 white paper | 1 | OpenDSS workflow + protection criteria + EPRI Ckt5/7/24 case studies |
| Rylander & Smith, EPRI TR-1026640 (2012) | 1 | Stochastic HCA in OpenDSS, protection metrics, 40-feeder dataset including EPRI family |
| Coogan, Reno & Grijalva, Sandia 2013 | 3 | **Direct EPRI Ckt7 in OpenDSS** — same feeder, same tool, 50% load condition documented |
| McDermott et al., PNNL-32230 (2021) | 3 | OpenDSS + EMT + HIL on EPRI J1; quantifies protection failure thresholds; CNN zonal classifier precedent |
| Krishnamoorthy, Sadnan & Dubey (2019) | 3 | EPRI Ckt-24 in OpenDSS; 50% inflection quantified |
| Prabakar et al., NREL/TP-5D00-82331 (2022) | 4 | EPRI J1 in OpenDSS, IBDER protection modeling, OpenDSS-PSCAD validation |
| Guzmán et al., IEEE TPWRS (2024) | 1 | Iterative HCA in OpenDSS with explicit relay-reach, fuse-coord, sympathetic-trip constraints |

---

## 6. Suggested Section Architecture for the Paper

1. **Section II.A — Test Feeder.** Cite [Coogan et al. 2013] and [EPRI DRIVE 2019] to justify EPRI Ckt7 as a documented OpenDSS benchmark.
2. **Section II.B — DER Placement Methodology.** Use the four-stage LSF → HCA → iterative protection-aware → zone-aware workflow. Cite Acharya 2006, Hung & Mithulananthan 2013, Rylander & Smith 2012, EPRI DRIVE 2019, Guzmán et al. 2024, Dharmasena et al. 2022.
3. **Section II.C — DER Sizing and 50% Penetration Justification.** Cite Krishnamoorthy et al. 2019, McDermott et al. 2021, Alcala-Gonzalez et al. 2021, Coogan et al. 2013, IEEE Std 1547.7-2013, IEEE Std 1547-2018.
4. **Section II.D — Standards Compliance.** Cite IEEE Std 1547-2018 (Category B), 1547.1-2020 (type-tested behavior), 1547.7-2013 (impact study framework).
5. **Related Work.** Use Cluster 4 to argue the placement-methodology gap — that ML fault classification papers consistently underspecify DER placement, and that your paper closes that gap.

---

## 7. Files in this Deliverable

| File | Contents |
|---|---|
| `DER_placement_justification_master_report.md` | This master report (executive overview, citation stack, ready-to-paste paragraph, section architecture) |
| `cluster1_hosting_capacity.md` | 10 HCA methodology sources, full per-source entries |
| `cluster2_optimal_placement.md` | 12 optimal placement and sizing sources, full per-source entries |
| `cluster3_penetration_impacts.md` | 10 DER penetration impact sources, full per-source entries |
| `cluster4_ml_fault_studies.md` | 10 ML fault classification sources with placement-decision comparison table |
| `cluster5_ieee_standards.md` | 6 IEEE standards with scope, key provisions, and application notes |

---

*Compiled May 14, 2026 for Theodore Lodge's undergraduate research on ML-based fault zone identification in DER-integrated distribution feeders. All cluster files contain full IEEE-style citations with DOIs and URLs.*
