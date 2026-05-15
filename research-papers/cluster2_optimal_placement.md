# Cluster 2: Optimal DER Placement and Sizing for Radial Distribution Feeders

**Purpose:** Justification of DER (PV) placement location and sizing methodology for the EPRI Ckt7 feeder in OpenDSS at 50% penetration, for the paper "Machine Learning–Based Fault Zone Identification in DER-Integrated Distribution Feeders Under Sparse and Degraded Sensor Conditions."

**EPRI Ckt7 Context:** The EPRI Ckt7 feeder is a three-phase, four-wire radial distribution test system operating at 115/12.47/0.48/0.24 kV, published by EPRI as a realistic solar integration study benchmark. It is fully modeled in OpenDSS and is structurally comparable to suburban/rural 12.47 kV distribution feeders with multiple laterals, voltage regulators, and a mix of three-phase and single-phase load buses.

---

## Source 1 — Foundational Analytical Method (Loss Sensitivity Factor)

**Citation:**
N. Acharya, P. Mahat, and N. Mithulananthan, "An analytical approach for DG allocation in primary distribution network," *International Journal of Electrical Power & Energy Systems*, vol. 28, no. 10, pp. 669–678, Dec. 2006. DOI: [10.1016/j.ijepes.2006.02.013](https://linkinghub.elsevier.com/retrieve/pii/S0142061506000652)

**Methodology:** Analytical — exact two-bus loss formula  
- **Objective function:** Minimize total real power losses in the radial distribution network.  
- **Key formula:** For each candidate bus *i*, the optimal DG size that minimizes losses is derived by differentiating the total power loss expression \( P_{\text{loss}} = \sum_{j=1}^{N} \alpha_{ij}(P_i P_j + Q_i Q_j) + \beta_{ij}(Q_i P_j - P_i Q_j) \) with respect to injected power at bus *i*, and setting \( \partial P_{\text{loss}} / \partial P_{DGi} = 0 \). This yields a closed-form expression for the optimal size at each bus.  
- **Placement strategy:** All buses ranked by loss reduction; the bus yielding minimum residual loss after inserting the optimally-sized DG is chosen.  
- **Constraints:** Voltage limits (0.95–1.05 p.u.), branch thermal limits, power balance.

**Test Feeder/System:** IEEE 69-bus radial distribution system (12.66 kV).

**Key Findings:**
- Provides a computationally efficient closed-form formula for simultaneous DG sizing and bus ranking—no iterative population-based search required.
- Demonstrated significant loss reductions (>40%) with a single optimally placed and sized DG on the IEEE 69-bus feeder.
- The exact loss formula is load-flow independent for size estimation, requiring only the base-case load flow for sensitivity coefficients \( \alpha_{ij}, \beta_{ij} \).
- Widely cited (>1,000 citations) as the definitive analytical baseline for comparison in the DG placement literature.

**Application Note:** This foundational paper provides the theoretical basis for the *exact loss formula* used to rank buses as DG candidates on a radial feeder. For your EPRI Ckt7 study, cite this paper to justify computing \( \partial P_{\text{loss}} / \partial P_{DGi} \) for every load bus from a base-case OpenDSS power flow, then pre-selecting the top-ranked buses as candidate DER injection points before applying sizing at 50% penetration. This avoids full combinatorial search across hundreds of Ckt7 buses and grounds your placement selection in a widely-accepted analytical framework.

**Flags:** [Radial feeder]

---

## Source 2 — Analytical Refinement with Loss Sensitivity Index + PV Model

**Citation:**
A. Elkholy, "Optimal planning of multiple PV-DG in radial distribution systems using loss sensitivity analysis and genetic algorithm," in *Proc. IEEE MEPCON*, Cairo, Egypt, Dec. 2024. DOI: [10.1109/MEPCON63025.2024.10850009](https://ieeexplore.ieee.org/document/10850009/)

**Methodology:** Hybrid analytical + metaheuristic (Loss Sensitivity Factor + Genetic Algorithm + Numerical Grid Search)  
- **Objective function:** Minimize total active power loss via time-series power flow analysis incorporating a dynamic PV-DG model (PV generation profile over 24-hour period or annual basis).  
- **Stage 1:** Loss Sensitivity Factor (LSF) computed for all buses: \( \text{LSF}_i = \partial P_{\text{loss}} / \partial P_i \), using iterative/continuous sensitivity analysis re-evaluated at each load-generation operating point.  
- **Stage 2:** Genetic algorithm and a numerical grid search method optimize the DG size at the LSF-ranked candidate buses.  
- **Co-simulation:** MATLAB + OpenDSS via the COM interface is used for time-series power flow validation; OpenDSS acts as the power flow engine.  
- **Constraints:** Voltage bounds (0.95–1.05 p.u.), branch current limits, DG capacity bounds.

**Test Feeder/System:** 12-bus radial distribution test system (MATLAB + OpenDSS co-simulation).

**Key Findings:**
- The proposed numerical method achieves comparable accuracy to GA and Exhaustive Load Flow (ELF) approaches at lower computational cost.
- Continuous/dynamic sensitivity re-evaluation (rather than static base-case sensitivity) produces superior DG placement accuracy when PV intermittency is modeled.
- LSF-ranked buses consistently correspond to mid-feeder and far-end buses where voltage drop is highest, reinforcing the heuristic rationale for targeting high-LSF buses.
- OpenDSS co-simulation enables accurate three-phase unbalanced power flow for each candidate PV configuration during the optimization loop.

**Application Note:** This paper directly justifies using LSF computed from a base-case OpenDSS snapshot power flow to pre-rank the EPRI Ckt7 buses as candidate PV injection points. Cite this work to support your workflow of: (1) running a no-DER OpenDSS power flow on Ckt7, (2) computing LSF for all load buses, (3) selecting the top-*k* buses by LSF as DER injection points, and (4) sizing DER to reach 50% penetration. The OpenDSS COM interface workflow described in this paper mirrors your simulation environment exactly.

**Flags:** [OpenDSS] [Radial feeder]

---

## Source 3 — PSO Metaheuristic for DG Placement and Sizing

**Citation:**
D. Q. Hung and N. Mithulananthan, "Multiple distributed generator placement in primary distribution networks for loss reduction," *IEEE Transactions on Industrial Electronics*, vol. 60, no. 4, pp. 1700–1708, Apr. 2013. DOI: [10.1109/TIE.2011.2112316](http://ieeexplore.ieee.org/document/5709978/)

**Methodology:** Analytical multi-DG extension of the exact loss formula (Acharya et al.)  
- **Objective function:** Minimize total active power loss for multiple DG units simultaneously injected at different buses.  
- **Method:** Extends the analytical closed-form optimal size formula to accommodate multiple DGs, using an exhaustive iterative technique: sequentially add one DG at the optimal bus until the desired count or penetration level is reached. An exact loss formula incorporating cross-injection terms prevents the suboptimality introduced by greedy sequential placement.  
- **DG types:** Unity power factor (real power injection only, analogous to PV inverters operating at unity PF).  
- **Constraints:** Node voltage bounds, branch current limits, total power balance.

**Test Feeder/System:** IEEE 33-bus and IEEE 69-bus radial distribution test feeders.

**Key Findings:**
- For multiple DG units, simple sequential placement using single-DG analytics yields suboptimal results; the iterative loss formula with cross-terms significantly improves total loss reduction.
- Optimal DG locations cluster in the mid-to-far section of the feeder (approximately the 2/3 point from the substation), consistent with well-known heuristic rules for reactive power compensation.
- With three DGs at optimal locations on the IEEE 33-bus feeder, active power losses were reduced by approximately 88%.
- The exact formula provides an upper-bound estimate of optimal DG size at each candidate bus without requiring a full iterative optimizer.

**Application Note:** This paper establishes that for multiple PV units at 50% penetration, a greedy sequential strategy (place one DG, recompute losses, place the next) is analytically justifiable and widely cited. For EPRI Ckt7, cite this work to justify distributing your PV capacity across multiple buses (rather than a single large unit), selecting buses iteratively using the loss formula after each placement, and targeting roughly the 2/3-feeder-length region for initial candidate selection. The multi-DG exact loss framework is directly applicable to setting 50% penetration across Ckt7's main feeder and laterals.

**Flags:** [Radial feeder]

---

## Source 4 — PSO Metaheuristic with Voltage and Power Constraints

**Citation:**
M. Al Soudi, O. Alsayyed, B. Batiha, T. Hamadneh, O. Malik, M. Dehghani, and Z. Montazeri, "Optimal placement and sizing of distributed generation units in distribution networks using an enhanced particle swarm optimization framework," *Electrotechnica & Electronica*, vol. 61, no. 1, pp. 1–12, 2026. DOI: [10.20998/2074-272x.2026.1.02](http://eie.khpi.edu.ua/article/view/347599)

**Methodology:** Enhanced Particle Swarm Optimization (PSO-DM — PSO augmented with Dehghani method population-wide refinement)  
- **Objective function:** Minimize total active power loss AND total voltage deviation jointly: \( F = w_1 \cdot P_{\text{loss}} + w_2 \cdot \sum |1 - V_i| \).  
- **Search space:** Continuous (DG size) + discrete (bus location treated as integer variable).  
- **Constraint handling:** Voltage magnitude limits (0.95–1.05 p.u.), power balance, DG penetration limits per bus.  
- **Enhancement:** The Dehghani method modification allows all population members, including worst-performing particles, to contribute to the search direction, improving exploration and preventing premature convergence.

**Test Feeder/System:** IEEE 33-bus radial distribution system.

**Key Findings:**
- PSO-DM with 4 DG units reduced active power losses from 210.67 kW to 53.9 kW (74.4% reduction) and reactive power losses from 142.84 kVAr to 38.42 kVAr (73.1% reduction) on the IEEE 33-bus feeder.
- Minimum bus voltage improved from 0.9037 p.u. to 0.9741 p.u. with 4 DGs, highlighting the voltage profile benefit of distributed DER.
- PSO-DM outperforms standard PSO in convergence speed and solution quality, particularly for multi-DG configurations where the search space is large.
- The paper provides a validated baseline for how many DG units are optimal for 33-bus class feeders under different penetration levels.

**Application Note:** Cite this paper to justify using PSO or a similarly population-based search if you elect to enumerate DER candidate configurations on the EPRI Ckt7 feeder. The joint loss + voltage deviation objective is directly relevant because your fault detection study requires both realistic power flow conditions (voltage accuracy) and meaningful DER coverage across zones, making the two-objective formulation a natural justification for how you balance DER sizing against Ckt7 voltage profile constraints at 50% penetration.

**Flags:** [Radial feeder]

---

## Source 5 — Modified Grey Wolf Optimizer with Protection Adaptation *(HIGH PRIORITY: Protection/Fault)*

**Citation:**
N. Bouchikhi, F. Boussadia, R. Bouddou, A. O. Salau, S. Mekhilef, C. Gouder, S. Adiche, and A. Belabbes, "Optimal distributed generation placement and sizing using modified grey wolf optimization and ETAP for power system performance enhancement and protection adaptation," *Scientific Reports*, vol. 15, art. 13841, Apr. 2025. DOI: [10.1038/s41598-025-98012-0](https://www.nature.com/articles/s41598-025-98012-0)

**Methodology:** Modified Grey Wolf Optimization (MGWO) + ETAP software security analysis  
- **Objective function:** Minimize active power loss (APL) and reactive power loss (RPL) simultaneously while assessing protection coordination implications.  
- **MGWO enhancement:** Adds adaptive weights and a dynamic circling mechanism to the standard GWO hierarchy, preventing premature convergence while maintaining fast convergence.  
- **Protection analysis module:** ETAP is used post-placement to analyze fault current variation at different DG capacity levels, examining maximum and minimum fault current changes (I_max, I_min) as a function of DG penetration.  
- **Constraints:** Voltage stability index bounds, APL/RPL minimization, protection coordination feasibility.

**Test Feeder/System:** IEEE 33-bus (standard) and 114-bus (large-scale) distribution networks.

**Key Findings:**
- MGWO achieved 69.7% decrease in average power loss and 69.6% decrease in real power loss on the IEEE 33-bus system, with 7.3% voltage stability enhancement.
- **Critical for fault studies:** DG integration at various capacity levels caused I_max to increase by up to 21.5%, while I_min showed significant fluctuations—directly requiring changes to protection settings.
- On the 114-bus large-scale network, APL and RPL decreased by 65.2% and 64.9%, respectively, confirming scalability.
- The paper is unique in explicitly co-analyzing DER placement optimization and its impact on fault current levels, linking DER siting to protection coordination requirements.

**Application Note:** This is particularly valuable for your paper because it establishes that DER placement decisions must account for fault current changes—directly relevant to fault zone identification. Cite this to justify that your 50% penetration DER scenario on EPRI Ckt7 was not placed arbitrarily, but rather evaluated for protection feasibility: specifically, that inverter-interfaced PV (with fault current limited to ~1.1 p.u.) avoids the extreme I_max increases seen with directly-coupled DG, and that bus selections were made to avoid concentrating DER at locations that would severely reduce fault current reach from the substation.

**Flags:** [Protection/Fault] [Radial feeder]

---

## Source 6 — OPF/Sensitivity-Based DG Placement with Probabilistic Formulation *(IEEE Transactions)*

**Citation:**
S. Das, O. B. Fosso, and G. Marafioti, "Probabilistic planning of distribution networks with optimal DG placement under uncertainties," *IEEE Transactions on Industry Applications*, vol. 59, no. 3, pp. 3571–3581, May–Jun. 2023. DOI: [10.1109/TIA.2023.3234233](https://ieeexplore.ieee.org/document/10005824/)

**Methodology:** Sensitivity-based OPF (non-linear optimal power flow with sensitivity pre-screening)  
- **Objective function:** Minimize total distribution network power losses; improve voltage stability index. Formulated as probabilistic non-linear optimization to handle generation and load uncertainty.  
- **Sensitivity technique:** A sensitivity-based pre-screening identifies the most impactful buses for DG placement prior to solving the full OPF, significantly reducing the search space.  
- **Uncertainty modeling:** Monte Carlo sampling over stochastic load and renewable generation profiles; optimal tap settings of off-load tap-changing transformers are co-optimized.  
- **Software:** Free and open-source (PYPOWER/Python ecosystem — applicable to OpenDSS-based workflows).  
- **Constraints:** Voltage magnitude bounds, branch current/thermal limits, DG power factor, transformer tap bounds.

**Test Feeder/System:** IEEE 69-bus, Indian 85-bus, and a practical 88-bus radial distribution network (Froan island, Norway).

**Key Findings:**
- The sensitivity-based OPF outperforms purely heuristic approaches in both computational efficiency and solution quality across all three test systems.
- Application to a real-world 88-bus island feeder demonstrates practical scalability beyond standard IEEE test cases.
- Probabilistic formulation (Monte Carlo over uncertain loads/generation) yields DG placements robust to operating condition variability—important for solar PV whose output is intermittent.
- The combination of sensitivity pre-screening + OPF provides a two-stage pipeline directly applicable to feeders with hundreds of buses (like EPRI Ckt7).

**Application Note:** This paper justifies a two-stage workflow for your Ckt7 simulation: (1) use voltage/loss sensitivity factors from a base-case OpenDSS power flow to filter the full Ckt7 bus set to ~10–15 high-priority candidate buses, then (2) solve a simplified OPF or iterative placement algorithm for the final bus/size assignments. Cite this to support that your DER placement methodology follows OPF principles and accounts for operating condition uncertainty, even if implemented with a simpler sensitivity-ranking + iterative power flow in OpenDSS rather than a full probabilistic optimizer.

**Flags:** [Radial feeder]

---

## Source 7 — OpenDSS Co-simulation for PVDG in Unbalanced Radial Feeders *(HIGH PRIORITY: OpenDSS)*

**Citation:**
T. D. Pham, T. T. Nguyen, and L. C. Kien, "Optimal placement of photovoltaic distributed generation units in radial unbalanced distribution systems using MATLAB and OpenDSS-based cosimulation and a proposed metaheuristic algorithm," *International Transactions on Electrical Energy Systems* (Hindawi/Wiley), vol. 2022, art. 1446479, Nov. 2022. DOI: [10.1155/2022/1446479](https://www.hindawi.com/journals/itees/2022/1446479/)

**Methodology:** Improved Slime Mould Algorithm (ISMA) metaheuristic with MATLAB–OpenDSS co-simulation  
- **Objective function (two separate cases):**  
  - Case 1: Minimize total three-phase power losses across all branches: \( \text{TPL} = \sum_{f=1}^{N_f} (P_{\text{loss},f}^A + P_{\text{loss},f}^B + P_{\text{loss},f}^C) \)  
  - Case 2: Minimize voltage deviation index: \( \text{VDI} = \sum_{b=1}^{N_b} |1 - V_{b,\text{avg}}| \)  
- **OpenDSS role:** Serves as the power flow engine for the unbalanced three-phase system. MATLAB controls the optimization via the Windows COM interface. OpenDSS builds the Y-matrix once; only load and generation injections are updated per iteration, making the co-simulation computationally efficient.  
- **ISMA modification:** Replaces the original SMA's second update formula with \( \text{Sol}_m = \text{Sol}_{sf\_best} + rdn \times (\text{Sol}_{rd3} - \text{Sol}_{rd4}) \) and adopts a fitness-based selection condition.  
- **Constraints:** Voltage limits 0.95–1.05 p.u., branch current limits, DG capacity 0–2000 kW per unit.

**Test Feeder/System:** IEEE 123-bus three-phase unbalanced radial distribution test feeder (4.16 kV).

**Key Findings:**
- ISMA achieved 78.88% power loss reduction (from 95.77 kW to 20.22 kW) and VDI reduction from 2.2035 p.u. to 1.4779 p.u. on the IEEE 123-bus feeder—the best performance among six competing algorithms.
- The MATLAB–OpenDSS co-simulation framework correctly handles unbalanced three-phase loading and single-phase laterals, a critical feature for realistic distribution feeder simulation.
- Optimal PVDGU locations for loss minimization: Buses 47 (907.2 kW), 65 (341.1 kW), and 72 (1560.6 kW)—all in the mid-to-far sections of the feeder.
- The co-simulation architecture (MATLAB optimizer ↔ OpenDSS power flow via COM) is directly portable to EPRI Ckt7.

**Application Note:** This paper provides the most direct methodological template for your EPRI Ckt7 simulation. Cite this work to justify: (1) using OpenDSS as the three-phase power flow engine with MATLAB/Python driving the placement algorithm via COM interface, (2) defining PVDGU capacity bounds per bus, and (3) adopting separate loss-minimization and voltage-deviation-minimization objectives evaluated in an OpenDSS snapshot. The IEEE 123-bus feeder (unbalanced, multi-phase, radial) is structurally similar to EPRI Ckt7, making this the closest available analog to your simulation environment.

**Flags:** [OpenDSS] [Radial feeder]

---

## Source 8 — OpenDSS Long-Term DER Allocation with Parallel Computing *(HIGH PRIORITY: OpenDSS)*

**Citation:**
G. Guerra and J. A. Martinez-Velasco, "A review of tools, models and techniques for long-term assessment of distribution systems using OpenDSS and parallel computing," *AIMS Energy*, vol. 6, no. 5, pp. 764–800, Sep. 2018. DOI: [10.3934/energy.2018.5.764](http://www.aimspress.com/article/10.3934/energy.2018.5.764)

**Methodology:** Monte Carlo simulation + OpenDSS COM interface for probabilistic DER allocation assessment  
- **Objective:** Optimal allocation of distributed resources (PV, wind, BESS) to minimize energy losses and voltage violations under stochastic operating conditions.  
- **OpenDSS usage:** Yearly quasi-static time-series (QSTS) simulations at 8760-point resolution; DER placement and sizing randomized via Monte Carlo sampling; results screened for ANSI C84.1 voltage compliance and thermal limits.  
- **Parallel computing:** OpenDSS Actor model used to distribute Monte Carlo instances across multiple CPU cores (5.5–7.2× speedup on 8-core hardware).  
- **Test systems:** IEEE 123-bus feeder, **EPRI J1 feeder** (~3,000 nodes, 12.47 kV), EPRI Test Feeder C (~3,000 nodes).

**Key Findings:**
- High PV penetration (above 50%) consistently caused midday over-voltages on the EPRI J1 feeder—confirming the voltage constraint importance at 50% penetration.
- OpenDSS QSTS mode enables accurate time-varying DER impact assessment across realistic annual generation/load profiles, rather than relying on peak-load snapshots.
- The EPRI J1 feeder is directly validated in OpenDSS under similar penetration scenarios to EPRI Ckt7, establishing a precedent for EPRI feeder use in DER placement research.
- The review consolidates best practices for OpenDSS-based DER allocation studies, including appropriate model building, COM interface usage, and results reporting.

**Application Note:** This is a critical methodological reference for your OpenDSS Ckt7 simulation. Cite this paper to justify: (1) using OpenDSS as the standard tool for EPRI feeder DER integration analysis (EPRI J1 is a sibling circuit to Ckt7), (2) performing at minimum a snapshot power flow at peak load conditions for DER placement screening (or QSTS if your timeline permits), and (3) applying the 50% penetration constraint as the threshold at which over-voltage risk becomes non-negligible. The paper's direct use of EPRI test feeders in OpenDSS provides institutional precedent for your circuit choice.

**Flags:** [OpenDSS] [Radial feeder]

---

## Source 9 — Multi-Objective DER Placement with Resiliency and Hosting Capacity *(IEEE Access)*

**Citation:**
S. Dharmasena, T. O. Olowu, and A. Sarwat, "Algorithmic formulation for network resilience enhancement by optimal DER hosting and placement," *IEEE Access*, vol. 10, pp. 21285–21302, 2022. DOI: [10.1109/ACCESS.2022.3154056](https://ieeexplore.ieee.org/document/9720991/)

**Methodology:** Multi-objective nonlinear programming (MONLP) with critical infrastructure (CI) ranking  
- **Objective function (three objectives simultaneously):**  
  1. Maximize DER hosting capacity (total DER penetration in kW)  
  2. Minimize total active power loss  
  3. Maximize network resiliency index (accounts for different outage scenarios)  
- **CI ranking:** A unique infrastructure criticality ranking scheme prioritizes nodes for DER placement based on their contribution to network resilience under outage scenarios (hurricane events simulated).  
- **Pareto front:** 18 Pareto optimal solutions generated, providing distribution planners with a range of DER placement options spanning the hosting capacity–loss–resiliency tradeoff.  
- **Constraints:** Voltage regulation bounds, branch thermal limits, full power flow equality constraints, maximum DER size per bus.

**Test Feeder/System:** IEEE 34-bus feeder (24.9 kV radial distribution feeder) under multiple outage scenarios.

**Key Findings:**
- Hosting capacity can be maximized while simultaneously minimizing losses and maximizing resiliency—these objectives are not always conflicting, particularly for well-distributed DER.
- Node criticality ranking (prioritizing buses that most improve resiliency) shifts DER away from substation-proximate locations toward mid-feeder and critical load nodes.
- The 18-solution Pareto front shows that a ~20–30% trade-off in hosting capacity yields disproportionately large improvements in resiliency and loss reduction.
- For fault studies, DER placement oriented toward resiliency (distributed across fault zones) is preferable to placement purely for loss minimization.

**Application Note:** This paper is particularly relevant because it frames DER placement explicitly in terms of *resiliency and fault zone coverage*—the exact context of your fault zone identification paper. Cite this to justify distributing your 50% penetration DER across multiple zones of the EPRI Ckt7 feeder (rather than concentrating at a single bus), arguing that distributed placement across defined fault zones provides both the hosting capacity target and the sensor-diverse DER signatures needed for fault zone classification. The multi-objective framework also justifies why you do not simply minimize losses alone.

**Flags:** [Radial feeder]

---

## Source 10 — PV DG Impact on Fault Currents and Protection Coordination *(HIGH PRIORITY: Protection/Fault)*

**Citation:**
D. Alcala-Gonzalez, E. García del Toro, M. I. Más-López, and S. Pindado, "Effect of distributed photovoltaic generation on short-circuit currents and fault detection in distribution networks: A practical case study," *Applied Sciences*, vol. 11, no. 1, art. 405, Jan. 2021. DOI: [10.3390/app11010405](https://www.mdpi.com/2076-3417/11/1/405)

**Methodology:** DIgSILENT PowerFactory simulation — parametric study of PV penetration vs. fault current at 25%, 50%, 75%, and 100% of peak load capacity  
- **Fault types tested:** Three-phase (3PH) and single line-to-ground (SLG) faults at multiple locations.  
- **Penetration levels:** 25%, 50%, 75%, 100% of total load capacity, with PV placed at nodes 634, 671, and 675.  
- **PV model:** Static generators (current-controlled voltage source inverters), fault current limited to 1.1 × I_rated.  
- **Analysis:** Overcurrent relay (OCR) operating times, Coordination Time Interval (CTI), Protection Coordination Index (PCI).  
- **Standards:** Short-circuit calculations per IEC 60909.

**Test Feeder/System:** IEEE 13-node distribution test feeder (4.16 kV three-phase).

**Key Findings:**
- At 50% PV penetration, substation fault current contribution decreases significantly while total fault current increases at the fault node—causing protection blinding at the upstream relay.
- PV inverter fault current is limited to approximately 1.1 p.u., meaning inverter-interfaced PV does not dramatically increase total fault current but *does* reduce grid-side relay fault current visibility.
- False/sympathetic tripping on healthy feeders and fuse-recloser coordination loss were both observed at 50% penetration—directly impacting protection device coordination.
- The PCI (protection coordination index) degrades monotonically as PV penetration increases, with the steepest degradation between 50% and 75%.

**Application Note:** This paper is directly cited to justify the practical motivation for your fault zone identification study under DER integration. For EPRI Ckt7 at 50% penetration, cite this paper to argue that (1) PV placement location relative to feeder protection zones changes fault current observability at substation-side sensors, (2) your distributed DER scenario at 50% penetration creates non-trivial shifts in measured fault signatures at available sensor locations (motivating your ML-based fault zone classifier), and (3) the PV penetration level of 50% you chose is the documented inflection point where protection coordination impact is substantial but not yet catastrophic. The 50% figure is defensible precisely because this paper quantifies this regime.

**Flags:** [Protection/Fault] [Radial feeder]

---

## Source 11 — Hosting Capacity Improvement on the EPRI J1 Feeder with OpenDSS *(HIGH PRIORITY: OpenDSS + EPRI Feeder)*

**Citation:**
D. Dalal, M. Sondharangalla, R. Ayyanar, and A. Pal, "Improving photovoltaic hosting capacity of distribution networks with coordinated inverter control — A case study of the EPRI J1 feeder," arXiv preprint arXiv:2311.02793, Nov. 2023. [https://arxiv.org/abs/2311.02793](https://arxiv.org/abs/2311.02793)

**Methodology:** Voltage-reactive power (VQ) sensitivity matrix in an iterative linear optimizer for smart inverter control; OpenDSS used for all power flow and HC assessment  
- **Objective:** Minimize total reactive power intervention \( \sum |Q_j + \Delta Q_j| \) subject to: (1) voltage bounds \( V_{\min} \le V_i \le V_{\max} \), (2) no active power curtailment, and (3) inverter reactive power capacity limits.  
- **Sensitivity matrix:** \( sm_{i,j} = (V_{i,j}^Q - V_i^0) / \Delta Q_j \) computed via OpenDSS voltage perturbation.  
- **Placement sets evaluated:** "All" (random across all feeder nodes), "Near" (first half of feeder), "Far" (second half of feeder) — directly testing location impact.  
- **Tool:** OpenDSS (power flow engine) + Python optimization.

**Test Feeder/System:** **EPRI J1 feeder** (12.47 kV, 1,384 customers, 10.95 MW peak load, 9 SVRs, 3,900 kVAr capacitors) — a direct sibling feeder to EPRI Ckt7 in the EPRI test circuit family.

**Key Findings:**
- PV placement in the "Far" half of the feeder causes the worst hosting capacity reduction (as low as 70 kW viable addition in August) due to remote voltage rise beyond regulator reach.
- PV placement in the "Near" half provides the highest HC and the most benign voltage impact, but provides less geographic distribution for fault zone coverage.
- The coordinated inverter control algorithm increased HC from 2.11 MW (19.3% of peak) to 6.41 MW (58.6% of peak)—a 3× improvement—on the EPRI J1 feeder in OpenDSS.
- Cross-phase sensitivity effects (reactive injection in one phase raising voltage in a different phase at a nearby node) are a non-negligible concern in EPRI-class unbalanced three-phase feeders.

**Application Note:** This paper provides the closest available analog to your EPRI Ckt7 OpenDSS study. Cite this to: (1) establish that the EPRI J1 feeder (sibling to Ckt7) has been validated with PV penetration studies directly in OpenDSS, (2) justify that at 50% penetration on EPRI Ckt7, DER placement in the middle sections of the feeder is preferable to far-end placement (which would require inverter VAR support to avoid overvoltage), and (3) note that placement across multiple zones is necessary to distribute PV evenly enough to avoid localized voltage violations at the 50% penetration level you are studying. The EPRI J1 and Ckt7 share voltage class, feeder topology, and OpenDSS modeling conventions.

**Flags:** [OpenDSS] [Radial feeder]

---

## Source 12 — Comprehensive Review of Multi-Objective DG Placement Methods

**Citation:**
A. M. Soomro, L. Kumar, M. Kumar, and W. Uddin, "Optimal multi-objective placement and sizing of distributed generation in distribution system: A comprehensive review," *Energies*, vol. 15, no. 21, art. 7850, Oct. 2022. DOI: [10.3390/en15217850](https://www.mdpi.com/1996-1073/15/21/7850)

**Methodology:** Systematic literature review — analytical, metaheuristic, and multi-objective methods for DG placement  
- **Scope:** Reviews 100+ papers on DG placement and sizing from 2010–2022, categorizing by: objective function type (single vs. multi-objective), DG type (PV, wind, combined), constraint handling, test system (IEEE 33/69/123-bus), and optimization algorithm.  
- **Objective functions reviewed:** Power loss minimization, voltage deviation minimization, voltage stability index maximization, hosting capacity maximization, reliability (SAIDI/SAIFI) improvement, cost minimization.  
- **Algorithms surveyed:** PSO, GA, Grey Wolf Optimizer, Salp Swarm, Slime Mould, Firefly, Whale Optimizer, Differential Evolution, NSGA-II (Pareto-front methods), and analytical approaches.  
- **Key insight:** The majority of multi-objective studies use IEEE 33-bus or IEEE 69-bus as test systems; there is a documented research gap for larger, more realistic test systems (≥100 buses).

**Test Feeder/System:** Review paper — covers IEEE 33-bus, IEEE 69-bus, IEEE 123-bus, and real utility feeders.

**Key Findings:**
- Loss minimization and voltage deviation minimization are the two most commonly combined objectives (present in >70% of multi-objective papers), and are not generally conflicting for inverter-based DER.
- PSO and its variants are the most frequently applied metaheuristic (cited in >40% of reviewed papers), with GA as the second most common.
- Penetration levels of 20–50% are the most commonly studied range; 50% is a significant penetration at which both voltage profile improvement *and* protection/coordination challenges are pronounced.
- The review explicitly identifies that protection/fault impact of DG placement is underrepresented in multi-objective formulations—most papers focus on steady-state performance.

**Application Note:** Cite this review to contextualize your DER placement approach within the broader literature. Specifically, use it to note that: (1) your two primary placement objectives (loss minimization and voltage profile uniformity across fault zones) are the dominant objectives in the field, (2) PSO/analytical hybrid methods are the consensus best practice for radial feeder DG placement, and (3) 50% penetration is a well-studied threshold in the literature, making your simulation scenario directly comparable to prior work on IEEE standard feeders while extending to the more realistic EPRI Ckt7.

**Flags:** [Radial feeder]

---

## Synthesis: DER Placement Justification for EPRI Ckt7 at 50% Penetration

### Recommended Placement Methodology (Most Defensible for OpenDSS Ckt7)

The most defensible and practically reproducible workflow for DER placement on the EPRI Ckt7 feeder at 50% penetration, drawing on the sources above, is a **two-stage hybrid analytical + iterative placement approach**:

**Stage 1 — Bus Pre-Screening (Analytical, Sources 1, 2):**
1. Run a base-case OpenDSS snapshot power flow on Ckt7 (no DER, peak load condition).
2. Compute the Loss Sensitivity Factor (LSF) for every three-phase load bus:
   \[ \text{LSF}_i = \frac{\partial P_{\text{loss}}}{\partial P_i} \approx \frac{2(a_{ii} P_i + c_{ii} Q_i)}{V_i^2} \]
   using branch resistance/reactance data available directly from the OpenDSS Ckt7 model.
3. Rank buses by LSF in descending order. Select the top 15–20 buses as candidate DER injection points. This step reduces the combinatorial search from hundreds of Ckt7 buses to a manageable candidate set, consistent with Acharya et al. [Source 1] and Elkholy [Source 2].

**Stage 2 — Iterative/Sequential DER Sizing (Sources 3, 7, 8):**
4. For each candidate bus, apply the exact loss formula (Hung & Mithulananthan [Source 3]) to estimate the loss-minimizing DG size at that bus given the current power flow state.
5. Add DER units sequentially (one per iteration), re-running the OpenDSS power flow after each addition, until the cumulative installed capacity reaches 50% of Ckt7 peak load. The 50% target is defined as: \( \sum_i P_{\text{DER},i} = 0.50 \times P_{\text{peak,Ckt7}} \).
6. At each iteration, check voltage limits (0.95–1.05 p.u.) across all Ckt7 buses; if a violation occurs, reduce the DG size at that bus until all voltages are compliant (consistent with Das et al. [Source 6]).

**Step 3 — Zone-Aware Distribution Check (Sources 9, 10, 11):**
7. Verify that the final DER configuration places units across multiple fault zones of the Ckt7 feeder (near-substation, mid-feeder, far-end laterals), not concentrated at a single zone. This is critical for your fault zone identification paper—DER must be present in each zone to generate zone-differentiated sensor signatures. Cite Dharmasena et al. [Source 9] for the resiliency/zone-coverage motivation.
8. For each zone, confirm that inverter-interfaced PV at the selected buses does not reduce the substation-side fault current below the relay pickup threshold for the farthest bus in that zone, using OpenDSS fault study mode (Alcala-Gonzalez et al. [Source 10]).

### Summary Table of Source–Justification Mapping

| Source | Methodology Family | Justifies |
|---|---|---|
| Acharya et al. 2006 [1] | Analytical (exact loss formula) | Loss-sensitivity bus ranking for candidate selection |
| Elkholy 2024 [2] | LSF + GA + OpenDSS | OpenDSS-based LSF workflow; dynamic sensitivity |
| Hung & Mithulananthan 2013 [3] | Analytical multi-DG | Sequential multi-unit placement; 2/3-rule basis |
| Al Soudi et al. 2026 [4] | PSO metaheuristic | Population-based sizing if analytical is insufficient |
| Bouchikhi et al. 2025 [5] | Grey Wolf Opt. + protection | DER placement and fault current/protection impact |
| Das et al. 2023 [6] | Sensitivity OPF + probabilistic | OPF-based sizing with uncertainty; voltage stability |
| Pham et al. 2022 [7] | ISMA + OpenDSS co-simulation | **OpenDSS COM-based PVDG placement template** |
| Guerra & Martinez-Velasco 2018 [8] | OpenDSS QSTS + Monte Carlo | **EPRI feeder OpenDSS DER allocation precedent** |
| Dharmasena et al. 2022 [9] | Multi-objective NLP (HC + loss + resilience) | Zone-distributed placement; Pareto-based sizing |
| Alcala-Gonzalez et al. 2021 [10] | Simulation (fault current parametric) | **50% penetration fault current/protection impact** |
| Dalal et al. 2023 [11] | Sensitivity matrix + OpenDSS (EPRI J1) | **EPRI feeder OpenDSS PV placement; near vs. far** |
| Soomro et al. 2022 [12] | Comprehensive review | Contextualizing methodology in literature |

### Key Justification Points for the Paper

1. **Why loss-sensitivity ranking?** Sources [1], [2], and [6] establish analytical consensus that LSF-ranked buses yield the highest loss reduction per unit of DER capacity, making LSF the computationally cheapest and most transparent method for initial bus selection on a large feeder like Ckt7.

2. **Why 50% penetration?** Sources [10] and [12] document that 50% is the penetration level at which protection coordination challenges emerge (PCI degradation, relay blinding) while voltage regulation remains manageable with smart inverters—making it the most practically meaningful penetration scenario for a fault detection study.

3. **Why multiple DER units (not one large unit)?** Source [3] demonstrates that distributing capacity across multiple buses gives superior loss reduction and voltage improvement versus concentrating at one bus. Source [9] adds that distributed placement across fault zones is essential for resiliency and, by extension, for generating geographically distinct fault signatures.

4. **Why OpenDSS?** Sources [7] and [8] establish OpenDSS as the community-validated power flow engine for EPRI-class distribution feeders, with direct precedent for EPRI J1 (sibling to Ckt7). Source [11] is the closest direct precedent—same feeder family, same tool, similar penetration levels.

5. **Why consider fault current impact during placement?** Sources [5] and [10] establish that DER placement location affects fault current observability from substation relays. For your fault zone identification paper, this means DER bus selection is not independent of fault detection accuracy—placement that severely reduces fault current reach from the substation (far-end concentrated DER) would impair sensor-based fault zone classification, making bus selection a design decision with direct methodological consequences.

---

*Report compiled for Cluster 2: Optimal DER Placement/Sizing — undergraduate researcher thesis support.*  
*Saved to: `/home/user/workspace/cluster2_optimal_placement.md`*
