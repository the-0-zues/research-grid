# IEEE Standards Layer: DER Interconnection and Distribution Impact Studies

**Purpose:** This document provides citation-ready summaries of the IEEE standards governing distributed energy resource (DER) interconnection and distribution impact studies. It supports the simulation setup section of an undergraduate paper on ML-based fault zone identification on DER-integrated feeders (EPRI Ckt7 in OpenDSS, 0% and 50% DER penetration). Each standard entry includes a full citation, scope, key technical provisions, and an application note explaining how to anchor DER size/placement assumptions and the 50% penetration scenario to formal requirements.

---

## 1. IEEE Std 1547-2018 — Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces

### Full IEEE-Style Citation

> IEEE Std 1547™-2018, *IEEE Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces*, IEEE, New York, NY, USA, published April 6, 2018 (Board Approval: February 15, 2018). DOI: [10.1109/IEEESTD.2018.8332112](https://doi.org/10.1109/IEEESTD.2018.8332112). Active Standard (under revision as P1547, PAR approved December 2022 through December 2026).

**Amendment:** IEEE Std 1547a™-2020, *Amendment 1: To Provide More Flexibility for Adoption of Abnormal Operating Performance Category III*, published 2020. Revises allowable trip clearing time ranges in Table 13 for Category III DERs to broaden adoption.

### Scope

IEEE Std 1547-2018 establishes mandatory technical specifications and performance requirements for the interconnection and interoperability of all DER technologies with electric power systems (EPS) at typical primary and secondary distribution voltages ([IEEE SA](https://standards.ieee.org/standard/1547-2018.html)). The standard is technology-neutral, covering synchronous machines, induction machines, and power inverter/converter-based DER (including solar PV, wind turbines, fuel cells, battery energy storage, and combined heat and power systems), with no upper nameplate capacity limit (the prior 10 MVA aggregate cap was removed in 2018). It addresses general requirements, voltage and reactive power control, response to abnormal conditions, power quality, islanding detection, interoperability, and test and verification requirements, applying to DER installed on radial primary and secondary distribution systems as well as secondary network systems ([NREL, "Highlights of IEEE Standard 1547-2018"](https://docs.nrel.gov/docs/fy20osti/75436.pdf)).

### Key Technical Provisions Relevant to DER Placement and Sizing

**Normal Operating Performance Categories (Voltage Regulation):**

IEEE 1547-2018 defines two performance categories for voltage regulation capability, assigned to DER by the Authority Governing Interconnection Requirements (AGIR):

| Feature / Control Mode | Category A | Category B |
|---|---|---|
| Description | Minimum capabilities; adequate for lower DER penetration | Extended capabilities; for high DER penetration with frequent large output variations |
| Constant Power Factor Mode | Required | Required |
| Constant Reactive Power Mode | Required | Required |
| Voltage-Reactive Power (Volt-VAR) Mode | Required | Required |
| Active Power–Reactive Power (Watt-VAR) Mode | Not Required | **Required** |
| Voltage–Active Power (Volt-Watt) Mode | Not Required | **Required** |

Category B is explicitly designed for feeders with high DER penetration where DER output varies frequently and significantly. The standard mandates that all DERs have reactive power injection and absorption capability: minimum 44% of rated capacity injecting (overexcited) and 25% to 44% absorbing (underexcited), depending on voltage level ([NREL, "Highlights of IEEE Standard 1547-2018"](https://docs.nrel.gov/docs/fy20osti/75436.pdf)).

**Abnormal Operating Performance Categories (Ride-Through):**

IEEE 1547-2018 defines three categories for response to abnormal grid conditions, each applying increasingly stringent voltage and frequency ride-through requirements ([NRECA Guide to IEEE 1547-2018](https://www.cooperative.com/programs-services/bts/documents/reports/nreca-guide-to-ieee-1547-2018-march-2019.pdf)):

| Category | Design Intent | Alignment |
|---|---|---|
| Category I | Minimum bulk system needs; achievable by all DER technologies including rotating machines | German grid code for synchronous generators |
| Category II | Full coordination with bulk power system stability; avoids tripping for wider range of disturbances | NERC PRC-024-2 |
| Category III | Bulk system and distribution support; for low-inertia, highly-penetrated grids | California Rule 21 and Hawaii Rule 14H |

Default voltage trip thresholds (p.u. of nominal) and clearing times (seconds) by category:

| Trip Level | Cat. I Trip Voltage | Cat. II Trip Voltage | Cat. III Trip Voltage | Cat. I Clear (s) | Cat. II Clear (s) | Cat. III Clear (s) |
|---|---|---|---|---|---|---|
| OV2 | 1.20 | 1.20 | 1.20 | 0.16 | 0.16 | 0.16 |
| OV1 | 1.10 | 1.10 | 1.10 | 2.0 | 2.0 | 13.0 |
| UV1 | 0.70 | 0.70 | 0.88 | 2.0 | 10.0 | 21.0 |
| UV2 | 0.45 | 0.45 | 0.50 | 0.16 | 0.16 | 2.0 |

Frequency defaults (identical for all three abnormal operating categories): OF2 = 62.0 Hz (0.16 s), OF1 = 61.2 Hz (300 s), UF1 = 58.5 Hz (300 s), UF2 = 56.5 Hz (0.16 s) ([NRECA Guide to IEEE 1547-2018](https://www.cooperative.com/programs-services/bts/documents/reports/nreca-guide-to-ieee-1547-2018-march-2019.pdf)).

**Rate of Change of Frequency (RoCoF) Ride-Through:** Category I = 0.5 Hz/s, Category II = 2.0 Hz/s, Category III = 3.0 Hz/s mandatory.

**Power Quality:** DC injection < 0.5% of rated output; harmonic distortion must comply with IEEE 519; voltage flicker must stay within prescribed limits; temporary overvoltage (TOV) contribution limited to ≤138% of nominal line-to-line voltage for no more than one fundamental frequency period ([Keentel Engineering: IEEE 1547-2018 Guide](https://www.keentelengineering.com/ieee-1547-2018-der-interconnection-standards)).

**Anti-Islanding:** DER must detect and cease to energize unintentional islands within 2 seconds.

**Interoperability:** All DER must support at least one communication protocol (IEEE 2030.5, DNP3/IEEE 1815, or SunSpec Modbus) and expose nameplate, monitoring, configuration, and management data with read response times ≤30 seconds.

**Applicability to OpenDSS simulation:** NREL's OpenDER model, integrated with OpenDSS via Python, has been validated against IEEE Std 1547-2018 control curves (Volt-VAR, Volt-Watt, Watt-VAR, Constant Power Factor, Constant Reactive Power modes), demonstrating that the standard can be directly implemented in OpenDSS simulation environments ([Lima et al., 2024, "OpenDER Model: Assessing IEEE Std 1547-2018 Voltage/Power Control Functions"](https://doi.org/10.1109/wcnps65035.2024.10814168)). NREL has also used OpenDSS to evaluate the impact of IEEE 1547-2018 voltage ride-through categories (I, II, III) on bulk power system dynamics following transmission-path faults ([NREL, "Assessment of IEEE 1547 Low-Voltage Ride-Through Criteria Impact"](https://docs.nrel.gov/docs/fy19osti/74432.pdf)).

### Application Note

**DER size assumptions:** DER units in your EPRI Ckt7 simulations can be cited as "sized in compliance with IEEE Std 1547-2018, applying technology-neutral interconnection requirements with reactive power capability conforming to the Category A minimum (44% injection, 25% absorption) at each point of common coupling." This anchors the choice to a formal standard rather than arbitrary selection.

**DER placement (Category B justification at 50% penetration):** IEEE 1547-2018 Clause 5 explicitly designates Category B capabilities as necessary "for high DER penetration, where the DER power output is subject to frequent large variations" ([NREL, "Highlights of IEEE Standard 1547-2018"](https://docs.nrel.gov/docs/fy20osti/75436.pdf)). For the 50% penetration scenario, you can state: "DERs are modeled with Category B volt-VAR and volt-watt capabilities per IEEE Std 1547-2018 Clause 5, reflecting the standard's provision for high-penetration feeder conditions."

**50% penetration scenario:** Category III abnormal performance was developed specifically for "highly-penetrated grids" (California Rule 21, Hawaii Rule 14H). A 50% DER penetration level on EPRI Ckt7 is a scenario directly contemplated by the 1547-2018 framework through its Category III performance tier and Category B voltage regulation tier; the standard explicitly supports penetration "approaching or exceeding 100% peak load" ([NREL, "IEEE 1547 and 2030 Standards for DER"](https://docs.nrel.gov/docs/fy15osti/63157.pdf)).

**Protection coordination context:** The ride-through voltage thresholds in Table 13 of IEEE 1547-2018 directly affect fault current contributions and protection coordination on DER-integrated feeders, making these settings a key variable for fault zone identification studies at different penetration levels.

---

## 2. IEEE Std 1547.1-2020 — Standard Conformance Test Procedures for Equipment Interconnecting Distributed Energy Resources with Electric Power Systems and Associated Interfaces

### Full IEEE-Style Citation

> IEEE Std 1547.1™-2020, *IEEE Standard Conformance Test Procedures for Equipment Interconnecting Distributed Energy Resources with Electric Power Systems and Associated Interfaces*, IEEE, New York, NY, USA, approved March 5, 2020, published May 21, 2020. DOI: [10.1109/IEEESTD.2020.9097534](https://doi.org/10.1109/IEEESTD.2020.9097534). Active Standard.

### Scope

IEEE Std 1547.1-2020 specifies the type, production, commissioning, and periodic tests and evaluations that must be performed to confirm that the interconnection and interoperation functions of equipment and systems interconnecting DERs with the EPS conform to IEEE Std 1547-2018 ([IEEE Xplore, 1547.1-2020](https://ieeexplore.ieee.org/document/9097534/)). The standard provides repeatable, location-independent test procedures that accommodate the full range of DER technologies. Conformance may be established through a combination of test types; no single test type alone is sufficient to establish full site compliance ([NRECA, "IEEE Standard 1547.1-2020 Approved"](https://www.cooperative.com/programs-services/bts/Documents/Advisories/Advisory-IEEE-1547-1-Approved-June-2020.pdf)).

### Key Technical Provisions Relevant to DER Placement and Sizing

**Test structure (five test types per IEEE 1547.1-2020):**

| Clause | Test Type | Primary Audience | Scope |
|---|---|---|---|
| Clause 5 | Type Tests | Manufacturers | >100 pages; laboratory verification that equipment meets all IEEE 1547-2018 functional requirements under controlled conditions |
| Clause 6 | Interoperability Tests | Manufacturers + Utilities | Verifies that signals through the DER communication interface are acted upon correctly per IEEE 1547-2018 Clause 10 |
| Clause 7 | Production Tests | Manufacturers | Performed on every manufactured unit; requires recognized testing agency (e.g., UL); verifies trip response to abnormal voltage and frequency, and synchronization |
| Clause 8 | DER Evaluations and Commissioning Tests | Utilities / Co-ops | 80 pages; verification for four DER connection complexity categories from simple Point-of-Connection units to large utility-scale facilities; includes design evaluation, as-built evaluation, and Basic/Detailed commissioning tests |
| Periodic Tests | Ongoing verification | DER operators | Scheduled re-verification over DER operational lifetime |

**Key commissioning provisions:** The Reference Point of Applicability (RPA) — the location where IEEE 1547-2018 interconnection performance requirements apply — must be identified for each DER installation. Commissioning tests verify actual field settings against type-tested parameters. Manufacturers had 18 months from IEEE 1547-2018 publication (i.e., until approximately October 2022) to certify equipment compliance with a Nationally Recognized Testing Laboratory (NRTL) such as Underwriters Laboratories ([NRECA, "IEEE Standard 1547.1-2020 Approved"](https://www.cooperative.com/programs-services/bts/Documents/Advisories/Advisory-IEEE-1547-1-Approved-June-2020.pdf)).

**Ride-through verification:** Type tests (Clause 5) specifically verify performance under IEEE 1547-2018 Table 13 voltage and frequency ride-through thresholds, producing certified performance evidence used in simulation modeling. NREL and Sandia have used hardware-in-the-loop (PHIL) test platforms to conduct IEEE 1547.1-compliant ride-through assessments on commercial PV inverters, demonstrating strong agreement between type-test results and in-situ distribution behavior ([Apablaza-Arancibia et al., 2021](https://doi.org/10.3390/en14216936)).

**Energy storage specific:** For ES DER, IEEE 1547.9-2022 (see Section 5) recommends extending the standard 1547.1 anti-islanding test from two output power levels to four: >90% exporting, >90% importing, 25–50% exporting, and 25–50% importing, to reflect the bidirectional nature of storage ([Sandia, "IEEE 1547.9-2022"](https://www.sandia.gov/app/uploads/sites/82/2022/10/105_Ropp_Innovative.pdf)).

### Application Note

**DER size assumptions:** DER units in your OpenDSS simulation can be described as "representative of IEEE Std 1547.1-2020 type-tested equipment, ensuring that voltage/frequency ride-through behavior and reactive power control modes assumed in simulation reflect certified performance characteristics." This links modeled inverter behavior to verified laboratory performance.

**DER placement:** Although IEEE 1547.1-2020 is primarily a compliance testing standard, its commissioning test provisions (Clause 8) establish that each DER site must be evaluated at its specific point of connection — implying that placement decisions carry test-verification obligations that the standard formalizes. The requirement for a commissioning test at the installed location anchors the concept that DER placement is a site-specific engineering decision, not merely a system-level choice.

**50% penetration:** At 50% penetration, the aggregate of type-tested DERs may interact in ways not captured by individual unit testing. The standard's periodic maintenance provision acknowledges that field behavior over a DER lifetime may deviate from type-test results, which is precisely the motivation for studying protection coordination at high penetration in simulation.

---

## 3. IEEE Std 1547.2-2008 and IEEE Std 1547.2-2023 — Application Guide for IEEE Std 1547

### Full IEEE-Style Citations

> IEEE Std 1547.2™-2008, *IEEE Application Guide for IEEE Std 1547, IEEE Standard for Interconnecting Distributed Resources with Electric Power Systems*, IEEE, New York, NY, USA, Board Approval: December 10, 2008, published April 15, 2009. Status: Inactive-Reserved (superseded by IEEE Std 1547.2-2023 on March 25, 2021). Cited in the Federal Energy Policy Act of 2005. [IEEE SA](https://standards.ieee.org/ieee/1547.2/3364/)

> IEEE Std 1547.2™-2023, *IEEE Application Guide for IEEE Std 1547™-2018, Standard for Interconnection and Interoperability of Distributed Energy Resources with Associated Electric Power Systems Interfaces*, IEEE, New York, NY, USA, published 2024. DOI: [10.1109/IEEESTD.2024.10534228](https://doi.org/10.1109/IEEESTD.2024.10534228). Active Standard. [IEEE Xplore](https://ieeexplore.ieee.org/document/10534228)

### Scope

**IEEE Std 1547.2-2008** (superseded): Provided technical background and application details to support the understanding of IEEE Std 1547-2003. It characterized various forms of distributed resource (DR) technologies and their interconnection issues, supplied background and rationale for the 1547-2003 technical requirements, and offered tips, techniques, and rules of thumb for project implementation. Intended for engineers, engineering consultants, and knowledgeable practitioners in the DR field ([IEEE SA, 1547.2-2008](https://standards.ieee.org/ieee/1547.2/3364/)).

**IEEE Std 1547.2-2023** (current): Provides technical background, rationale, and guidance to support application of the substantially revised IEEE Std 1547-2018. It describes how the requirements and default settings in 1547-2018 balance distribution and bulk system needs for increasing DER penetration, and expands on the base standard by addressing DER integration issues not fully covered in 1547-2018, including reclosing coordination and limitation of overvoltage in the Area EPS ([IEEE SCC21](https://sagroups.ieee.org/scc21/standards/ieee-std-1547-2-2008/)). The guide includes technical descriptions, schematics, application guidance, and interconnection examples.

### Key Technical Provisions Relevant to DER Placement and Sizing

IEEE Std 1547.2-2023 addresses five major topic areas that extend the base standard's applicability to real-world DER deployment decisions:

1. **Performance Category Assignment:** Explains the concept of the newly introduced performance categories (Category A/B for normal operation; Categories I/II/III for abnormal operation) and the role of the Authority Governing Interconnection Requirements (AGIR) in assigning specific categories to DER at specific feeder locations. This is directly relevant to modeling DER with different ride-through and voltage regulation profiles on EPRI Ckt7.

2. **Voltage and Reactive Power Control:** Provides expanded guidance on volt-VAR, volt-watt, watt-VAR, and constant reactive power modes, including parameter selection methodology and interaction with existing voltage regulation equipment (LTCs, capacitor banks, regulators).

3. **Frequency Control:** Covers frequency droop implementation, inertial response, and ROCOF ride-through, with system-specific parameter selection guidance.

4. **Response to Abnormal Conditions:** Addresses ride-through implementation in practice, including the ranges of adjustability for control settings and voltage/frequency trip settings to account for specific feeder characteristics — directly applicable to protection studies on DER-integrated feeders.

5. **Reclosing Coordination and Overvoltage Limitation:** Covers two integration issues explicitly excluded from the base standard — automatic reclosing behavior on feeders with DER (a critical protection concern in fault zone identification studies) and the limitation of temporary overvoltage (TOV) contribution from DER, which affects protection relay settings.

The guide also covers interoperability and communication interface requirements, test and verification practices, and design/as-built installation evaluations for utility-scale DER.

### Application Note

**DER size assumptions:** IEEE Std 1547.2-2023 explains the rationale behind the default settings and capability requirements in IEEE 1547-2018, providing the engineering justification to use standard default reactive power settings and ride-through thresholds in simulation. You can cite it as the interpretive reference for why specific Category A or Category B parameters were selected for DER units in your model.

**DER placement:** The guide's treatment of reclosing coordination (a topic absent from the base standard) is particularly relevant to placement decisions on radial feeders like EPRI Ckt7. Placement near recloser locations or mid-feeder on radials changes reclosing interaction, making the application guide a justification for evaluating protection impacts as a function of DER location.

**50% penetration:** The guide explicitly addresses "increasing DER penetration" as the core motivation for many of the 1547-2018 revisions, and the AGIR category assignment process is designed to be feeder-specific — meaning that high-penetration feeders like the 50% scenario may warrant Category B normal performance and Category III abnormal performance assignments, both of which are described in detail in this guide.

---

## 4. IEEE Std 1547.7-2013 — Guide for Conducting Distribution Impact Studies for Distributed Resource Interconnection *(Critical)*

### Full IEEE-Style Citation

> IEEE Std 1547.7™-2013, *IEEE Guide for Conducting Distribution Impact Studies for Distributed Resource Interconnection*, IEEE, New York, NY, USA, Board Approval: December 11, 2013, published February 28, 2014. Status: Inactive-Reserved (inactivated March 21, 2024; successor project P1547.7 "Guide for Conducting Impact Studies for Distributed Energy Resource Interconnection" has an active PAR approved June 6, 2024, superseding the 2013 version). [IEEE SA, 1547.7-2013](https://standards.ieee.org/ieee/1547.7/4572/)

**Note on successor project:** P1547.7 (PAR approved 2024, Working Group Chair: Frank Goodman) is actively updating the 2013 guide with expanded scope to include aggregated DER, ES DER, and modern feeder topologies ([IEEE SA, P1547.7](https://standards.ieee.org/ieee/1547.7/11690/)).

### Scope

IEEE Std 1547.7-2013 provides alternative approaches and good engineering practices for conducting studies of the potential impacts of a distributed resource (DR) or aggregate DR interconnected to an electric power distribution system ([IEEE SA, 1547.7-2013](https://standards.ieee.org/ieee/1547.7/4572/)). The guide describes criteria, scope, and extent for five categories of engineering studies, where study scope and extent are functions of identifiable characteristics of the DR, the EPS, and the interconnection. The guide promotes consistency in impact studies and limits the studies performed to those technically justified by specific DR-EPS characteristics, preventing both under-study and over-study. It does not presume IEEE 1547 compliance, does not interpret the base standard, and does not add requirements beyond those in other IEEE 1547 series documents. The updated P1547.7 project expands coverage to include methodology for aggregated DER and explicitly addresses criteria for determining mitigation.

### Key Technical Provisions Relevant to DER Placement and Sizing

**Tiered Study Methodology:**

IEEE 1547.7-2013 employs a three-tier approach to determine which engineering studies are necessary for any given DER interconnection ([NREL, "IEEE 1547 and 2030 Standards for DER"](https://docs.nrel.gov/docs/fy15osti/63157.pdf)):

| Tier | Study Level | Purpose |
|---|---|---|
| Tier 1 | Preliminary Review (Screening Assessment) | Simple yes/no tests; if passed, interconnection approved without detailed study |
| Tier 2 | Conventional Impact Studies | Required if preliminary screens indicate possible issues; covers steady-state and protection impacts |
| Tier 3 | Special Impact Studies | Required for complex scenarios; covers transient, dynamic, and rare protection coordination issues |

**Five Study Types:**

1. **Screening Assessment:** Simple binary screens based on DER size relative to feeder capacity (e.g., the widely cited 15% aggregate generation-to-peak-load screen from FERC SGIP practice, which IEEE 1547.7 contextualizes in a technically transparent framework). A 50% penetration level substantially exceeds typical preliminary screening thresholds, triggering mandatory progression to Tier 2 studies.

2. **Steady-State Studies:** Electrical power flow and voltage analyses under normal operating and contingency conditions, including voltage rise/drop, thermal loading, and voltage regulation device interactions. For a 50% DER penetration feeder (EPRI Ckt7), steady-state studies would evaluate voltage profiles along the feeder under peak generation and minimum load conditions.

3. **Transient and Dynamic Studies:** Includes power quality issues such as harmonics, voltage flicker, rapid voltage change, and other stability issues. The guide recognizes that as aggregate DER increases, individual-unit power quality effects accumulate and may exceed feeder tolerance.

4. **Impacts on Area EPS Protection, Communications, and Control:** This is the most directly relevant study type for fault zone identification research. It addresses how DER alters fault current magnitude and direction, affects protection relay coordination, changes recloser-fuse coordination, and may create protection blind spots or false trips. The guide provides criteria for evaluating whether DER causes protection coordination failures.

5. **Other Studies:** Studies not falling into the preceding four categories, including islanding assessment, TOV analysis, and grounding compatibility.

**Aggregate DER considerations:** IEEE 1547.7-2013 explicitly addresses the "impacts of aggregated DER on an Area EPS" — meaning that studying a 50% penetration scenario is precisely within the standard's methodological scope for aggregate impact assessment. The guide recommends iterative analysis as DER penetration increases, recognizing that impacts may be non-linear.

**Screening context:** FERC's Small Generator Interconnection Procedures (SGIP) use a 15% aggregate generating capacity to peak load screen as a preliminary criterion; the revised SGIP added a 100% of minimum daytime load screen to complement this ([NREL, "DER Interconnection Roadmap"](https://www.nrel.gov/docs/fy21osti/78643.pdf)). A 50% penetration scenario on EPRI Ckt7 would fail both the 15% peak load screen and the daytime load screen under most loading conditions, necessitating full Tier 2 (conventional) impact studies per the 1547.7 framework.

### Application Note

**This is the methodological anchor for your entire simulation study.** IEEE 1547.7-2013 provides the formal engineering framework that justifies conducting the impact studies you are performing in OpenDSS. You can cite it as follows: "The simulation study follows the IEEE Std 1547.7-2013 five-study framework, specifically addressing steady-state impacts (voltage profiles at 0% and 50% penetration) and impacts on Area EPS protection (fault current magnitude, fault zone identification difficulty, and protection coordination changes introduced by DER)."

**DER size assumptions:** IEEE 1547.7-2013 defines study scope as a function of DER characteristics (size, technology, point of connection), meaning that the DER sizes chosen for EPRI Ckt7 should be selected to represent technically meaningful penetration increments — precisely the 0% and 50% points you have chosen — that bracket screening thresholds and test the boundaries of conventional versus special impact study requirements.

**DER placement:** The guide explicitly makes study scope a function of DER placement characteristics relative to the EPS. Feeder-end vs. mid-feeder DER placement changes voltage profiles, fault current distribution, and protection impacts in ways the guide contemplates. This justifies studying placement as an independent variable in the 50% scenario.

**50% penetration:** A 50% aggregate DER penetration level definitionally exceeds all standard preliminary screening thresholds documented in industry practice and FERC SGIP, triggering full conventional and special impact studies under the 1547.7 framework. This makes the 50% scenario not an arbitrary choice but a formally study-triggering condition under the IEEE 1547.7 methodology.

---

## 5. IEEE Std 1547.9-2022 — Guide for Application of IEEE Std 1547 to the Interconnection of Energy Storage Distributed Energy Resources to Electric Power Systems

### Full IEEE-Style Citation

> IEEE Std 1547.9™-2022, *IEEE Guide for Application of IEEE Std 1547 to the Interconnection of Energy Storage Distributed Energy Resources to Electric Power Systems*, IEEE, New York, NY, USA, Board Approval: June 16, 2022, published August 5, 2022. [IEEE SA, 1547.9-2022](https://standards.ieee.org/ieee/1547.9/10875/). Active Standard.

### Scope

IEEE Std 1547.9-2022 describes the application of IEEE Std 1547-2018 specifically to the interconnection of energy storage distributed energy resources (ES DER) to electric power systems ([IEEE SA, 1547.9-2022](https://standards.ieee.org/ieee/1547.9/10875/)). Its scope includes all ES DER capable of exporting active power to an EPS (i.e., capable of serving load simultaneously with the Area EPS). Systems in scope include PV + battery storage hybrids and vehicle-to-grid (V2G) systems; systems explicitly out of scope include uninterruptible power supplies (UPS, which cannot export to the grid) and vehicle-to-load-only (V1G) systems. The guide provides application examples, guidance on prudent technically sound interconnection approaches, ES DER-specific terminology, and identifies energy-storage topics not fully addressed in IEEE Std 1547-2018, setting a basis for future best-practice development ([Sandia National Laboratories, "IEEE 1547 for 2024 LDES Workshop"](https://www.sandia.gov/app/uploads/sites/256/2024/09/IEEE-1547-for-2024-LDES-Workshop-final.pdf)).

### Key Technical Provisions Relevant to DER Placement and Sizing

**ES DER-Specific Terminology (foundational for sizing and dispatch modeling):**

- **Operational State of Charge (SoC):** The usable energy stored as a proportion of operational capacity, expressed as a percentage — distinct from rated SoC.
- **Operational Capacity:** The energy an ES DER can provide on discharge subject to operational constraints (rated energy, state of health, discharge rate, temperature, usable SoC range).

**Functional Provisions unique to energy storage:**

| Provision | Description |
|---|---|
| Black Start / System Restoration | ES DER with isochronous control may energize intentional islands and assist in restoring de-energized feeder sections — relevant to post-fault restoration on DER-integrated feeders |
| Fast Frequency Response (FFR) | Covers synthetic inertia (power ∝ df/dt) deployment; ES DER can provide synthetic inertial response that pure generation DER cannot |
| Volt-VAR Support | Clarifies volt-VAR support modes for bidirectional ES DER (both charging and discharging states) |
| Anti-Islanding Test Modifications | Recommends testing at four power levels (>90% export, >90% import, 25–50% export, 25–50% import) vs. the two levels in IEEE 1547.1-2020 for unidirectional generation DER |
| Interoperability (Clause 10 additions) | Adds ES-specific parameters to IEEE 1547-2018 Table 29 reporting requirements, including operational SoC, operational capacity, and storage mode |
| ES DER in Secondary Networks | Addresses unique grounding and protection considerations for ES DER on secondary distribution networks |

**Ride-through exemptions and adjustments:** The guide clarifies voltage and frequency ride-through exemptions specific to ES DER operational states (e.g., when storage is fully charged and cannot absorb additional energy) and recommends appropriate operational responses.

**Secondary literature:** The complete set of IEEE 1547.9-2022 provisions is described in detail in a Sandia National Laboratories presentation from the 2024 LDES Workshop ([Sandia National Laboratories, "IEEE 1547 for 2024 LDES Workshop"](https://www.sandia.gov/app/uploads/sites/256/2024/09/IEEE-1547-for-2024-LDES-Workshop-final.pdf)) and an earlier 2021 Sandia presentation on the P1547.9 draft ([Sandia National Laboratories, "IEEE P1547.9," 2021](https://www.sandia.gov/app/uploads/sites/273/2021/12/1_Ropp_Mike_SNL_MicrogridsES_Session4_12-3-2021.pdf)).

### Application Note

**DER size assumptions:** If your 50% penetration scenario includes battery energy storage (BESS) as part of the DER mix, IEEE Std 1547.9-2022 is the governing companion to IEEE 1547-2018 for sizing and operational modeling. Cite it to justify ES DER dispatch profiles: "ES DER are modeled in compliance with IEEE Std 1547.9-2022, which requires that only ES DER capable of active power export are subject to IEEE 1547-2018 interconnection requirements, and operational SoC is tracked per the standard's definitions."

**DER placement:** The guide's black-start and system restoration provisions are relevant when ES DER are placed at strategic feeder locations — a factor your fault zone identification study should consider if storage DER near faulted zones can re-energize feeder sections and obscure fault detection.

**50% penetration:** At 50% DER penetration, the mix of generation-only DER (PV) and bidirectional ES DER creates fundamentally different fault current profiles than a purely generation-based scenario. IEEE Std 1547.9-2022 provides the framework for distinguishing these cases in a standards-compliant manner, justifying the separate modeling of ES and non-ES DER within the penetration scenario.

---

## 6. IEEE Std 2030.7-2017 and IEEE Std 2030.8-2018 — Microgrid Controller Standards (Brief)

### Full IEEE-Style Citations

> IEEE Std 2030.7™-2017, *IEEE Standard for the Specification of Microgrid Controllers*, IEEE, New York, NY, USA, Board Approval: December 6, 2017, published April 23, 2018. [IEEE SA, 2030.7-2017](https://standards.ieee.org/ieee/2030.7/5941/). Active Standard.

> IEEE Std 2030.8™-2018, *IEEE Standard for the Testing of Microgrid Controllers*, IEEE, New York, NY, USA, Board Approval: June 14, 2018, published August 24, 2018. [IEEE SA, 2030.8-2018](https://standards.ieee.org/ieee/2030.8/6169/). Active Standard.

### Scope and Brief Description

**IEEE Std 2030.7-2017** specifies the functions above the component control level associated with the proper operation of the Microgrid Energy Management System (MEMS), applicable to all microgrids regardless of topology, configuration, or jurisdiction ([IEEE SA, 2030.7-2017](https://standards.ieee.org/ieee/2030.7/5941/)). The MEMS encompasses control functions that enable the microgrid to manage itself, operate autonomously or grid-connected, and seamlessly connect to and disconnect from the main distribution grid for the exchange of power and provision of ancillary services. Testing procedures for these functions are also addressed. The standard focuses on functional specifications, not hardware design.

**IEEE Std 2030.8-2018** develops testing procedures to verify, quantify, and compare the performance of microgrid controller functions against expected minimum requirements ([IEEE SA, 2030.8-2018](https://standards.ieee.org/ieee/2030.8/6169/)). It is functionality-driven, using a modular approach to verify the functional requirements specified in IEEE 2030.7-2017, and presents metrics comparing performance from both the microgrid operator and Distribution System Operator (DSO) perspectives.

**Relationship to the IEEE 1547 series:** IEEE Std 2030.7/2030.8 govern microgrid-level control functions, while IEEE 1547-2018 governs individual DER interconnection requirements. The 2030.7 standard's grid-connected operation mode requires that the microgrid's aggregated DER behavior conform to the Area EPS operational requirements defined in IEEE 1547-2018. The standards are complementary: 1547 governs each inverter's interface with the grid; 2030.7 governs the supervisory controller coordinating multiple DERs within a microgrid boundary ([IEEE SA, "IEEE Standards for the Evolving DER Ecosystem"](https://standards.ieee.org/beyond-standards/ieee-standards-for-the-evolving-distributed-energy-resources-der-ecosystem/)).

### Key Technical Provisions (relevant to grid-connected DER operation)

- **Grid-connected operation mode:** IEEE 2030.7-2017 requires seamless transition between grid-connected and islanded modes, power exchange with the main distribution grid, and provision of ancillary services.
- **Autonomous operation mode:** Defines islanded operation requirements, relevant to anti-islanding compliance under IEEE 1547-2018.
- **Performance metrics (2030.8-2018):** Quantifies transition time, voltage and frequency recovery characteristics, and power dispatch accuracy — all relevant when modeling DER-integrated feeder behavior in OpenDSS.

### Application Note

For a feeder-level DER fault zone identification study, IEEE 2030.7/2030.8 have limited direct applicability unless your simulation explicitly models microgrid-controlled DER clusters on EPRI Ckt7. However, if DER units in the 50% penetration scenario are coordinated through a MEMS (as might be the case for utility-managed DER fleets), the grid-connected operational behavior governed by IEEE 2030.7-2017 constrains how DER units respond during and following a fault event. You can cite these standards briefly as: "Grid-connected DER operation in the simulation follows the functional framework of IEEE Std 2030.7-2017 for microgrid controller behavior, which complements the IEEE 1547-2018 DER-level interconnection requirements." These standards are most relevant to scenarios involving coordinated DER response rather than uncoordinated rooftop-scale PV, and their inclusion is warranted primarily if your paper explicitly models active DER management systems.

---

## Synthesis: How IEEE Standards Anchor Your DER Placement Section

The five IEEE standards surveyed in this document form a hierarchical technical framework that converts simulation design choices into formally justified engineering decisions. At the top level, **IEEE Std 1547-2018** establishes the non-negotiable performance envelope for every DER unit in your OpenDSS model: voltage ride-through thresholds, reactive power capability, and the Category A/B distinction that differentiates standard-deployment DER from high-penetration-optimized DER — making the 50% penetration case not an arbitrary scenario but a formally recognized operational tier within the standard. **IEEE Std 1547.1-2020** closes the loop between simulation and physical equipment by confirming that the modeled inverter behaviors (volt-VAR curves, ride-through profiles) reflect type-tested, commissioned equipment performance rather than idealized assumptions. **IEEE Std 1547.2-2023** provides the interpretive bridge, explaining how Category A/B assignments and ride-through parameter ranges should be selected for specific feeder conditions — particularly for reclosing coordination and overvoltage limitation, both of which directly affect fault zone identification accuracy on radial feeders. Most critically for this paper, **IEEE Std 1547.7-2013** provides the entire methodological justification for conducting your impact studies at 0% and 50% penetration: a 50% aggregate DER penetration definitionally exceeds standard screening thresholds, requiring formal steady-state studies (voltage profiles, thermal loading) and protection impact studies (fault current distribution, relay coordination) — precisely the study types your simulation implements in OpenDSS. Together, these standards establish that choosing EPRI Ckt7 with two penetration levels, sizing DER to meet Category A/B requirements, and studying protection behavior under IEEE 1547-2018 ride-through settings is not an arbitrary experimental design but a rigorously standards-anchored simulation methodology aligned with the industry's formal framework for evaluating DER integration on distribution feeders.

---

*Report compiled from primary sources: [IEEE Standards Association](https://standards.ieee.org), [NREL Publications](https://nrel.gov), [Sandia National Laboratories](https://sandia.gov), [NRECA Technical Advisories](https://cooperative.com), and peer-reviewed literature via IEEE Xplore. All citations include source URLs.*
