"""Create and populate the synthetic healthcare SQLite database (40 tables).

Domains covered:
  Provider (organizations, facilities, providers, credentials, networks, contracts)
  Member / Plan (health plans, benefits, members, eligibility, PCP assignment)
  Clinical (appointments, encounters, diagnoses, procedures, labs, vitals, pharmacy)
  Claims (claims, lines, payments, denials, prior auth, referrals)
  File operations (submitters, file submissions, validation, approval, load stages)

All data is synthetic and generated with a fixed random seed so runs are reproducible.
Run directly:  python -m healthcare_agents.seed_data
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

SEED = 42
START = date(2025, 1, 1)
END = date(2026, 9, 30)

FIRST = ["James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael", "Linda", "David", "Elizabeth",
         "William", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen",
         "Daniel", "Nancy", "Matthew", "Lisa", "Anthony", "Betty", "Mark", "Sandra", "Steven", "Ashley",
         "Priya", "Arjun", "Wei", "Mei", "Carlos", "Sofia", "Ahmed", "Fatima", "Hiroshi", "Aiko"]
LAST = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez",
        "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
        "Lee", "Patel", "Kumar", "Chen", "Nguyen", "Kim", "Singh", "Reddy", "Clark", "Lewis"]
CITIES = [("Dallas", "TX"), ("Houston", "TX"), ("Austin", "TX"), ("Phoenix", "AZ"), ("Chicago", "IL"),
          ("Atlanta", "GA"), ("Denver", "CO"), ("Seattle", "WA"), ("Miami", "FL"), ("Boston", "MA"),
          ("Columbus", "OH"), ("Charlotte", "NC")]
SPECIALTIES = [("207Q00000X", "Family Medicine"), ("207R00000X", "Internal Medicine"), ("208000000X", "Pediatrics"),
               ("207RC0000X", "Cardiology"), ("207N00000X", "Dermatology"), ("2084N0400X", "Neurology"),
               ("207X00000X", "Orthopedic Surgery"), ("207V00000X", "Obstetrics & Gynecology"),
               ("2084P0800X", "Psychiatry"), ("207RE0101X", "Endocrinology"), ("207RG0100X", "Gastroenterology"),
               ("207RX0202X", "Oncology"), ("207P00000X", "Emergency Medicine"), ("208600000X", "General Surgery"),
               ("207W00000X", "Ophthalmology")]
DIAGNOSES = [("E11.9", "Type 2 diabetes mellitus without complications", "Endocrine"),
             ("I10", "Essential (primary) hypertension", "Circulatory"),
             ("J45.909", "Unspecified asthma, uncomplicated", "Respiratory"),
             ("E78.5", "Hyperlipidemia, unspecified", "Endocrine"),
             ("M54.5", "Low back pain", "Musculoskeletal"),
             ("F32.9", "Major depressive disorder, single episode", "Mental Health"),
             ("F41.1", "Generalized anxiety disorder", "Mental Health"),
             ("J06.9", "Acute upper respiratory infection", "Respiratory"),
             ("N39.0", "Urinary tract infection", "Genitourinary"),
             ("I25.10", "Atherosclerotic heart disease", "Circulatory"),
             ("K21.9", "Gastro-esophageal reflux disease", "Digestive"),
             ("E66.9", "Obesity, unspecified", "Endocrine"),
             ("J44.9", "Chronic obstructive pulmonary disease", "Respiratory"),
             ("N18.3", "Chronic kidney disease, stage 3", "Genitourinary"),
             ("Z00.00", "General adult medical exam", "Preventive"),
             ("C50.919", "Malignant neoplasm of breast", "Oncology"),
             ("I48.91", "Atrial fibrillation", "Circulatory"),
             ("M17.11", "Primary osteoarthritis, right knee", "Musculoskeletal"),
             ("G43.909", "Migraine, unspecified", "Nervous System"),
             ("O80", "Encounter for full-term uncomplicated delivery", "Pregnancy")]
PROCEDURES = [("99213", "Office visit, established patient, low complexity", "E&M", 110),
              ("99214", "Office visit, established patient, moderate complexity", "E&M", 165),
              ("99203", "Office visit, new patient, low complexity", "E&M", 150),
              ("99285", "Emergency department visit, high severity", "Emergency", 650),
              ("93000", "Electrocardiogram, complete", "Cardiology", 60),
              ("80053", "Comprehensive metabolic panel", "Lab", 45),
              ("85025", "Complete blood count with differential", "Lab", 30),
              ("83036", "Hemoglobin A1C", "Lab", 40),
              ("71046", "Chest X-ray, 2 views", "Radiology", 95),
              ("73721", "MRI lower extremity joint", "Radiology", 1200),
              ("27447", "Total knee arthroplasty", "Surgery", 18500),
              ("45378", "Diagnostic colonoscopy", "GI", 2100),
              ("90834", "Psychotherapy, 45 minutes", "Behavioral", 140),
              ("90471", "Immunization administration", "Preventive", 25),
              ("99396", "Preventive visit, 40-64 years", "Preventive", 210),
              ("59400", "Routine obstetric care, vaginal delivery", "Obstetrics", 6200),
              ("96413", "Chemotherapy administration, IV", "Oncology", 900),
              ("97110", "Therapeutic exercise", "Therapy", 70)]
LAB_TESTS = [("4548-4", "Hemoglobin A1c", "%", 4.0, 5.6), ("2345-7", "Glucose", "mg/dL", 70, 99),
             ("2093-3", "Total Cholesterol", "mg/dL", 125, 200), ("2085-9", "HDL Cholesterol", "mg/dL", 40, 90),
             ("13457-7", "LDL Cholesterol", "mg/dL", 0, 100), ("2160-0", "Creatinine", "mg/dL", 0.6, 1.3),
             ("718-7", "Hemoglobin", "g/dL", 12.0, 17.5), ("6690-2", "WBC Count", "10^3/uL", 4.5, 11.0),
             ("3016-3", "TSH", "mIU/L", 0.4, 4.0), ("1742-6", "ALT", "U/L", 7, 56)]
MEDICATIONS = [("Metformin 500mg", "metformin", "Antidiabetic", 0), ("Lisinopril 10mg", "lisinopril", "ACE Inhibitor", 0),
               ("Atorvastatin 20mg", "atorvastatin", "Statin", 0), ("Albuterol Inhaler", "albuterol", "Bronchodilator", 0),
               ("Sertraline 50mg", "sertraline", "SSRI", 0), ("Amlodipine 5mg", "amlodipine", "Calcium Channel Blocker", 0),
               ("Omeprazole 20mg", "omeprazole", "PPI", 0), ("Levothyroxine 50mcg", "levothyroxine", "Thyroid", 0),
               ("Insulin Glargine", "insulin glargine", "Insulin", 0), ("Apixaban 5mg", "apixaban", "Anticoagulant", 1),
               ("Oxycodone 5mg", "oxycodone", "Opioid Analgesic", 1), ("Adalimumab Pen", "adalimumab", "Biologic", 1),
               ("Semaglutide Pen", "semaglutide", "GLP-1 Agonist", 1), ("Amoxicillin 500mg", "amoxicillin", "Antibiotic", 0),
               ("Gabapentin 300mg", "gabapentin", "Anticonvulsant", 0)]
DENIAL_REASONS = [("CO-16", "Claim lacks information needed for adjudication", "Administrative"),
                  ("CO-18", "Duplicate claim or service", "Administrative"),
                  ("CO-29", "Time limit for filing has expired", "Timely Filing"),
                  ("CO-50", "Non-covered service: not medically necessary", "Medical Necessity"),
                  ("CO-97", "Service included in another service already adjudicated", "Bundling"),
                  ("CO-197", "Precertification/authorization absent", "Authorization"),
                  ("CO-27", "Expenses incurred after coverage terminated", "Eligibility"),
                  ("CO-109", "Claim not covered by this payer", "Eligibility"),
                  ("CO-151", "Payment adjusted: frequency of service exceeded", "Medical Necessity"),
                  ("CO-4", "Procedure code inconsistent with modifier", "Coding")]
VALIDATION_RULES = [("VR001", "File header present and well formed", "STRUCTURE", "CRITICAL"),
                    ("VR002", "Record count matches trailer", "STRUCTURE", "CRITICAL"),
                    ("VR003", "NPI is 10 digits and passes Luhn check", "FORMAT", "HIGH"),
                    ("VR004", "Required provider name populated", "COMPLETENESS", "HIGH"),
                    ("VR005", "Taxonomy code is valid NUCC code", "REFERENCE", "MEDIUM"),
                    ("VR006", "Effective date <= termination date", "BUSINESS", "HIGH"),
                    ("VR007", "No duplicate provider records in file", "UNIQUENESS", "MEDIUM"),
                    ("VR008", "State and ZIP code are valid", "FORMAT", "LOW"),
                    ("VR009", "Tax ID (TIN) is 9 digits", "FORMAT", "HIGH"),
                    ("VR010", "License not expired", "BUSINESS", "MEDIUM"),
                    ("VR011", "Member ID exists in eligibility", "REFERENCE", "HIGH"),
                    ("VR012", "Claim amounts are non-negative", "BUSINESS", "CRITICAL")]

SCHEMA = """
CREATE TABLE organizations (org_id INTEGER PRIMARY KEY, org_name TEXT, org_type TEXT, tax_id TEXT, city TEXT, state TEXT, created_date DATE);
CREATE TABLE facilities (facility_id INTEGER PRIMARY KEY, org_id INTEGER REFERENCES organizations, facility_name TEXT, facility_type TEXT, bed_count INTEGER, city TEXT, state TEXT, zip TEXT);
CREATE TABLE specialties (specialty_id INTEGER PRIMARY KEY, taxonomy_code TEXT, specialty_name TEXT);
CREATE TABLE providers (provider_id INTEGER PRIMARY KEY, npi TEXT UNIQUE, first_name TEXT, last_name TEXT, gender TEXT, provider_type TEXT, org_id INTEGER REFERENCES organizations, primary_specialty_id INTEGER REFERENCES specialties, status TEXT, accepting_new_patients INTEGER, created_date DATE);
CREATE TABLE provider_specialties (provider_id INTEGER REFERENCES providers, specialty_id INTEGER REFERENCES specialties, is_primary INTEGER, board_certified INTEGER, PRIMARY KEY (provider_id, specialty_id));
CREATE TABLE provider_locations (location_id INTEGER PRIMARY KEY, provider_id INTEGER REFERENCES providers, facility_id INTEGER REFERENCES facilities, address TEXT, city TEXT, state TEXT, zip TEXT, phone TEXT, is_primary INTEGER);
CREATE TABLE provider_credentials (credential_id INTEGER PRIMARY KEY, provider_id INTEGER REFERENCES providers, credential_type TEXT, license_number TEXT, issuing_state TEXT, issue_date DATE, expiration_date DATE, status TEXT);
CREATE TABLE networks (network_id INTEGER PRIMARY KEY, network_name TEXT, network_type TEXT, region TEXT);
CREATE TABLE provider_network_participation (participation_id INTEGER PRIMARY KEY, provider_id INTEGER REFERENCES providers, network_id INTEGER REFERENCES networks, effective_date DATE, termination_date DATE, tier TEXT, status TEXT);
CREATE TABLE provider_contracts (contract_id INTEGER PRIMARY KEY, provider_id INTEGER REFERENCES providers, org_id INTEGER REFERENCES organizations, contract_type TEXT, reimbursement_method TEXT, fee_schedule_pct REAL, start_date DATE, end_date DATE, status TEXT);
CREATE TABLE health_plans (plan_id INTEGER PRIMARY KEY, plan_name TEXT, line_of_business TEXT, plan_type TEXT, metal_tier TEXT, network_id INTEGER REFERENCES networks, monthly_premium REAL, deductible REAL, oop_max REAL);
CREATE TABLE plan_benefits (benefit_id INTEGER PRIMARY KEY, plan_id INTEGER REFERENCES health_plans, benefit_category TEXT, copay REAL, coinsurance_pct REAL, requires_prior_auth INTEGER);
CREATE TABLE members (member_id INTEGER PRIMARY KEY, member_number TEXT UNIQUE, first_name TEXT, last_name TEXT, date_of_birth DATE, gender TEXT, city TEXT, state TEXT, zip TEXT, phone TEXT, risk_score REAL, created_date DATE);
CREATE TABLE member_eligibility (eligibility_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, plan_id INTEGER REFERENCES health_plans, effective_date DATE, termination_date DATE, coverage_status TEXT, relationship TEXT);
CREATE TABLE member_pcp_assignments (assignment_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, effective_date DATE, end_date DATE, assignment_reason TEXT);
CREATE TABLE appointments (appointment_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, facility_id INTEGER REFERENCES facilities, appointment_date DATE, appointment_type TEXT, status TEXT);
CREATE TABLE encounters (encounter_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, facility_id INTEGER REFERENCES facilities, encounter_date DATE, encounter_type TEXT, admit_date DATE, discharge_date DATE, length_of_stay INTEGER);
CREATE TABLE diagnosis_codes (dx_code TEXT PRIMARY KEY, description TEXT, category TEXT, is_chronic INTEGER);
CREATE TABLE procedure_codes (cpt_code TEXT PRIMARY KEY, description TEXT, category TEXT, standard_charge REAL);
CREATE TABLE encounter_diagnoses (encounter_id INTEGER REFERENCES encounters, dx_code TEXT REFERENCES diagnosis_codes, sequence INTEGER, is_primary INTEGER, PRIMARY KEY (encounter_id, dx_code));
CREATE TABLE encounter_procedures (encounter_procedure_id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters, cpt_code TEXT REFERENCES procedure_codes, units INTEGER, procedure_date DATE);
CREATE TABLE lab_tests (lab_test_id INTEGER PRIMARY KEY, loinc_code TEXT, test_name TEXT, unit TEXT, ref_low REAL, ref_high REAL);
CREATE TABLE lab_results (lab_result_id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters, member_id INTEGER REFERENCES members, lab_test_id INTEGER REFERENCES lab_tests, result_value REAL, abnormal_flag TEXT, result_date DATE);
CREATE TABLE vital_signs (vital_id INTEGER PRIMARY KEY, encounter_id INTEGER REFERENCES encounters, member_id INTEGER REFERENCES members, systolic_bp INTEGER, diastolic_bp INTEGER, heart_rate INTEGER, temperature_f REAL, weight_lb REAL, height_in REAL, bmi REAL, recorded_date DATE);
CREATE TABLE medications (medication_id INTEGER PRIMARY KEY, drug_name TEXT, generic_name TEXT, drug_class TEXT, is_specialty INTEGER);
CREATE TABLE pharmacies (pharmacy_id INTEGER PRIMARY KEY, pharmacy_name TEXT, pharmacy_type TEXT, npi TEXT, city TEXT, state TEXT);
CREATE TABLE prescriptions (prescription_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, medication_id INTEGER REFERENCES medications, pharmacy_id INTEGER REFERENCES pharmacies, fill_date DATE, days_supply INTEGER, quantity INTEGER, refills INTEGER, ingredient_cost REAL, member_copay REAL);
CREATE TABLE claims (claim_id INTEGER PRIMARY KEY, claim_number TEXT UNIQUE, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, encounter_id INTEGER REFERENCES encounters, plan_id INTEGER REFERENCES health_plans, claim_type TEXT, service_date DATE, received_date DATE, adjudicated_date DATE, billed_amount REAL, allowed_amount REAL, paid_amount REAL, member_responsibility REAL, claim_status TEXT);
CREATE TABLE claim_lines (claim_line_id INTEGER PRIMARY KEY, claim_id INTEGER REFERENCES claims, line_number INTEGER, cpt_code TEXT REFERENCES procedure_codes, dx_code TEXT REFERENCES diagnosis_codes, units INTEGER, billed_amount REAL, allowed_amount REAL, paid_amount REAL, line_status TEXT);
CREATE TABLE claim_payments (payment_id INTEGER PRIMARY KEY, claim_id INTEGER REFERENCES claims, payment_date DATE, payment_amount REAL, payment_method TEXT, check_eft_number TEXT);
CREATE TABLE denial_reasons (denial_code TEXT PRIMARY KEY, description TEXT, category TEXT);
CREATE TABLE claim_denials (denial_id INTEGER PRIMARY KEY, claim_id INTEGER REFERENCES claims, denial_code TEXT REFERENCES denial_reasons, denial_date DATE, appealed INTEGER, appeal_outcome TEXT);
CREATE TABLE prior_authorizations (auth_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, provider_id INTEGER REFERENCES providers, cpt_code TEXT REFERENCES procedure_codes, request_date DATE, decision_date DATE, status TEXT, urgency TEXT);
CREATE TABLE referrals (referral_id INTEGER PRIMARY KEY, member_id INTEGER REFERENCES members, referring_provider_id INTEGER REFERENCES providers, referred_to_provider_id INTEGER REFERENCES providers, specialty_id INTEGER REFERENCES specialties, referral_date DATE, status TEXT, reason TEXT);
CREATE TABLE submitter_users (user_id INTEGER PRIMARY KEY, username TEXT UNIQUE, full_name TEXT, organization TEXT, role TEXT, email TEXT, active INTEGER);
CREATE TABLE file_submissions (file_id TEXT PRIMARY KEY, file_name TEXT, file_type TEXT, submitted_by INTEGER REFERENCES submitter_users, submitted_at DATETIME, record_count INTEGER, file_size_kb INTEGER, current_stage TEXT, current_status TEXT, last_updated DATETIME);
CREATE TABLE validation_rules (rule_id TEXT PRIMARY KEY, rule_description TEXT, rule_category TEXT, severity TEXT);
CREATE TABLE file_validation_results (validation_id INTEGER PRIMARY KEY, file_id TEXT REFERENCES file_submissions, rule_id TEXT REFERENCES validation_rules, validated_at DATETIME, result TEXT, error_count INTEGER, error_message TEXT);
CREATE TABLE file_approvals (approval_id INTEGER PRIMARY KEY, file_id TEXT REFERENCES file_submissions, approver_name TEXT, decision TEXT, decision_at DATETIME, comments TEXT);
CREATE TABLE file_load_stages (load_id INTEGER PRIMARY KEY, file_id TEXT REFERENCES file_submissions, stage_name TEXT, stage_order INTEGER, status TEXT, started_at DATETIME, completed_at DATETIME, records_loaded INTEGER, records_rejected INTEGER);
"""


def _d(r: random.Random, start: date = START, end: date = END) -> date:
    return start + timedelta(days=r.randint(0, (end - start).days))


def _ts(r: random.Random, day: date) -> datetime:
    return datetime(day.year, day.month, day.day, r.randint(7, 19), r.randint(0, 59), r.randint(0, 59))


def _phone(r: random.Random) -> str:
    return f"({r.randint(200, 989)}) {r.randint(200, 999)}-{r.randint(1000, 9999)}"


def build_database(db_path: str | Path, force: bool = False) -> Path:
    db_path = Path(db_path)
    if db_path.exists() and not force:
        return db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    r = random.Random(SEED)
    con = sqlite3.connect(db_path)
    con.executescript(SCHEMA)
    ins = lambda table, rows: rows and con.executemany(
        f"INSERT INTO {table} VALUES ({','.join('?' * len(rows[0]))})", rows)

    # ---- Provider domain ----
    org_types = ["Hospital System", "Medical Group", "Clinic", "IPA", "FQHC"]
    orgs = []
    for i in range(1, 31):
        city, st = r.choice(CITIES)
        orgs.append((i, f"{r.choice(LAST)} {r.choice(['Health', 'Medical Group', 'Care Partners', 'Physicians', 'Clinic'])}",
                     r.choice(org_types), f"{r.randint(10, 99)}-{r.randint(1000000, 9999999)}", city, st, _d(r, date(2015, 1, 1), date(2024, 12, 31))))
    ins("organizations", orgs)

    fac_types = ["Hospital", "Ambulatory Surgery Center", "Urgent Care", "Primary Care Clinic", "Imaging Center", "Lab"]
    facilities = []
    for i in range(1, 61):
        org = r.choice(orgs)
        ft = r.choice(fac_types)
        facilities.append((i, org[0], f"{org[4]} {ft} #{i}", ft, r.randint(50, 600) if ft == "Hospital" else 0,
                           org[4], org[5], f"{r.randint(10000, 99999)}"))
    ins("facilities", facilities)
    ins("specialties", [(i + 1, c, n) for i, (c, n) in enumerate(SPECIALTIES)])

    providers, prov_spec, prov_loc, creds, contracts = [], [], [], [], []
    for i in range(1, 301):
        org = r.choice(orgs)
        spec = r.randint(1, len(SPECIALTIES))
        status = r.choices(["ACTIVE", "INACTIVE", "PENDING", "TERMINATED"], [80, 8, 7, 5])[0]
        ptype = r.choices(["MD", "DO", "NP", "PA"], [60, 15, 15, 10])[0]
        providers.append((i, f"1{r.randint(100000000, 999999999)}", r.choice(FIRST), r.choice(LAST), r.choice("MF"),
                          ptype, org[0], spec, status, int(r.random() < 0.7), _d(r, date(2018, 1, 1), date(2025, 6, 30))))
        prov_spec.append((i, spec, 1, int(r.random() < 0.85)))
        if r.random() < 0.3:
            s2 = r.randint(1, len(SPECIALTIES))
            if s2 != spec:
                prov_spec.append((i, s2, 0, int(r.random() < 0.5)))
        for k in range(r.randint(1, 2)):
            fac = r.choice(facilities)
            prov_loc.append((len(prov_loc) + 1, i, fac[0], f"{r.randint(100, 9999)} {r.choice(['Main', 'Oak', 'Elm', 'Park', 'Lake', 'Hill'])} St",
                             fac[5], fac[6], fac[7], _phone(r), int(k == 0)))
        for ctype in ["State Medical License", "DEA Registration", "Board Certification"]:
            iss = _d(r, date(2015, 1, 1), date(2024, 1, 1))
            exp = iss + timedelta(days=r.choice([730, 1095, 1825]))
            creds.append((len(creds) + 1, i, ctype, f"{ctype[:2].upper()}{r.randint(100000, 999999)}", org[5], iss, exp,
                          "EXPIRED" if exp < date(2026, 10, 1) else "ACTIVE"))
        cs = _d(r, date(2022, 1, 1), date(2025, 12, 31))
        contracts.append((i, i, org[0], r.choice(["Fee-for-Service", "Capitation", "Value-Based", "Bundled Payment"]),
                          r.choice(["% of Medicare", "Per Member Per Month", "Case Rate", "DRG"]), round(r.uniform(90, 145), 1),
                          cs, cs + timedelta(days=1095), r.choices(["ACTIVE", "EXPIRED", "PENDING"], [75, 15, 10])[0]))
    ins("providers", providers)
    ins("provider_specialties", prov_spec)
    ins("provider_locations", prov_loc)
    ins("provider_credentials", creds)
    ins("provider_contracts", contracts)

    networks = [(1, "Premier PPO Network", "PPO", "National"), (2, "Select HMO Network", "HMO", "South"),
                (3, "Value EPO Network", "EPO", "West"), (4, "Medicare Advantage Network", "HMO", "National"),
                (5, "Medicaid Community Network", "HMO", "Midwest"), (6, "Narrow Exchange Network", "EPO", "Northeast")]
    ins("networks", networks)
    part = []
    for p in providers:
        for n in r.sample(networks, r.randint(1, 3)):
            eff = _d(r, date(2020, 1, 1), date(2025, 6, 30))
            term = eff + timedelta(days=r.randint(365, 2000)) if r.random() < 0.2 else None
            part.append((len(part) + 1, p[0], n[0], eff, term, r.choice(["Tier 1", "Tier 2", "Tier 3"]),
                         "TERMINATED" if term and term < date(2026, 10, 1) else "ACTIVE"))
    ins("provider_network_participation", part)

    # ---- Member / plan domain ----
    plans = []
    lobs = [("Commercial", "PPO", 1), ("Commercial", "HMO", 2), ("Exchange", "EPO", 6), ("Medicare Advantage", "HMO", 4),
            ("Medicaid", "HMO", 5), ("Commercial", "EPO", 3)]
    for i, tier in enumerate(["Bronze", "Silver", "Gold", "Platinum"] * 3, start=1):
        lob, ptype, net = lobs[(i - 1) % len(lobs)]
        prem = {"Bronze": 320, "Silver": 450, "Gold": 580, "Platinum": 720}[tier] * (0.6 if lob == "Medicaid" else 1)
        plans.append((i, f"{lob} {ptype} {tier}", lob, ptype, tier, net, round(prem, 2),
                      {"Bronze": 6500, "Silver": 4000, "Gold": 1500, "Platinum": 500}[tier],
                      {"Bronze": 9100, "Silver": 8000, "Gold": 6000, "Platinum": 3500}[tier]))
    ins("health_plans", plans)
    benefits = []
    for p in plans:
        for cat in ["Primary Care", "Specialist", "Emergency Room", "Urgent Care", "Inpatient", "Generic Rx", "Specialty Rx", "Imaging"]:
            benefits.append((len(benefits) + 1, p[0], cat, r.choice([0, 20, 30, 40, 75, 250]), r.choice([0, 10, 20, 30]),
                             int(cat in ("Inpatient", "Specialty Rx", "Imaging"))))
    ins("plan_benefits", benefits)

    members, elig, pcp = [], [], []
    pcp_providers = [p for p in providers if p[7] in (1, 2, 3) and p[8] == "ACTIVE"]
    for i in range(1, 1501):
        city, st = r.choice(CITIES)
        dob = _d(r, date(1940, 1, 1), date(2024, 1, 1))
        members.append((i, f"M{100000 + i}", r.choice(FIRST), r.choice(LAST), dob, r.choice("MF"), city, st,
                        f"{r.randint(10000, 99999)}", _phone(r), round(r.lognormvariate(0, 0.5), 3), _d(r, date(2020, 1, 1), date(2025, 1, 1))))
        plan = r.choice(plans)
        eff = _d(r, date(2023, 1, 1), date(2025, 6, 1))
        term = _d(r, date(2025, 7, 1), END) if r.random() < 0.15 else None
        elig.append((len(elig) + 1, i, plan[0], eff, term, "TERMED" if term else "ACTIVE",
                     r.choices(["Subscriber", "Spouse", "Dependent"], [60, 20, 20])[0]))
        pcp.append((i, i, r.choice(pcp_providers)[0], eff, term, r.choice(["Member Selected", "Auto Assigned", "Plan Assigned"])))
    ins("members", members)
    ins("member_eligibility", elig)
    ins("member_pcp_assignments", pcp)
    member_plan = {e[1]: e[2] for e in elig}

    # ---- Clinical domain ----
    ins("diagnosis_codes", [(c, d, cat, int(cat in ("Endocrine", "Circulatory", "Mental Health") or c in ("J44.9", "N18.3")))
                            for c, d, cat in DIAGNOSES])
    ins("procedure_codes", PROCEDURES)
    ins("lab_tests", [(i + 1, *t) for i, t in enumerate(LAB_TESTS)])
    ins("medications", [(i + 1, *m) for i, m in enumerate(MEDICATIONS)])
    pharmacies = []
    for i in range(1, 26):
        city, st = r.choice(CITIES)
        pharmacies.append((i, f"{r.choice(['CVS', 'Walgreens', 'Rite Aid', 'Kroger', 'Community', 'Express Scripts'])} Pharmacy #{r.randint(100, 9999)}",
                           r.choice(["Retail", "Mail Order", "Specialty"]), f"1{r.randint(100000000, 999999999)}", city, st))
    ins("pharmacies", pharmacies)

    active_prov = [p for p in providers if p[8] == "ACTIVE"]
    appts = []
    for i in range(1, 2501):
        appts.append((i, r.randint(1, len(members)), r.choice(active_prov)[0], r.choice(facilities)[0], _d(r),
                      r.choice(["New Patient", "Follow-up", "Annual Physical", "Telehealth", "Procedure"]),
                      r.choices(["COMPLETED", "CANCELLED", "NO_SHOW", "SCHEDULED"], [70, 12, 8, 10])[0]))
    ins("appointments", appts)

    encounters, enc_dx, enc_px, labs, vitals = [], [], [], [], []
    for i in range(1, 4001):
        etype = r.choices(["Outpatient", "Inpatient", "Emergency", "Telehealth", "Preventive"], [55, 8, 12, 15, 10])[0]
        d = _d(r)
        los = r.randint(1, 9) if etype == "Inpatient" else 0
        m = r.randint(1, len(members))
        encounters.append((i, m, r.choice(active_prov)[0], r.choice(facilities)[0], d, etype,
                           d if los else None, d + timedelta(days=los) if los else None, los))
        for seq, dx in enumerate(r.sample(DIAGNOSES, r.randint(1, 3)), start=1):
            enc_dx.append((i, dx[0], seq, int(seq == 1)))
        for px in r.sample(PROCEDURES, r.randint(1, 3)):
            enc_px.append((len(enc_px) + 1, i, px[0], r.randint(1, 2), d))
        if r.random() < 0.45:
            for t in r.sample(range(len(LAB_TESTS)), r.randint(1, 4)):
                _, _, _, lo, hi = LAB_TESTS[t]
                spread = {"4548-4": (4.5, 12.5), "2345-7": (65, 320)}.get(LAB_TESTS[t][0], (lo * 0.7, hi * 1.4))
                val = round(r.uniform(*spread), 2)
                labs.append((len(labs) + 1, i, m, t + 1, val, "H" if val > hi else "L" if val < lo else "N", d))
        if etype != "Telehealth":
            h = round(r.uniform(58, 76), 1)
            w = round(r.uniform(110, 290), 1)
            vitals.append((len(vitals) + 1, i, m, r.randint(100, 170), r.randint(60, 105), r.randint(55, 110),
                           round(r.uniform(97.0, 101.5), 1), w, h, round(703 * w / (h * h), 1), d))
    ins("encounters", encounters)
    ins("encounter_diagnoses", enc_dx)
    ins("encounter_procedures", enc_px)
    ins("lab_results", labs)
    ins("vital_signs", vitals)

    rx = []
    for i in range(1, 3001):
        med = r.randint(1, len(MEDICATIONS))
        spec = MEDICATIONS[med - 1][3]
        cost = round(r.uniform(800, 6500) if spec else r.uniform(4, 180), 2)
        rx.append((i, r.randint(1, len(members)), r.choice(active_prov)[0], med, r.randint(1, len(pharmacies)), _d(r),
                   r.choice([30, 60, 90]), r.choice([30, 60, 90, 1]), r.randint(0, 5), cost, round(min(cost, r.choice([0, 5, 10, 25, 50, 150])), 2)))
    ins("prescriptions", rx)

    # ---- Claims domain ----
    ins("denial_reasons", DENIAL_REASONS)
    proc_map = {p[0]: p for p in PROCEDURES}
    dx_by_enc: dict[int, list[str]] = {}
    for e, dx, *_ in enc_dx:
        dx_by_enc.setdefault(e, []).append(dx)
    px_by_enc: dict[int, list[tuple]] = {}
    for row in enc_px:
        px_by_enc.setdefault(row[1], []).append(row)
    claims, lines, payments, denials = [], [], [], []
    for i, enc in enumerate(encounters, start=1):
        if r.random() < 0.08:
            continue
        cid = len(claims) + 1
        svc = enc[4]
        rec = svc + timedelta(days=r.randint(1, 45))
        status = r.choices(["PAID", "DENIED", "PENDED", "PARTIALLY_PAID", "IN_REVIEW"], [68, 12, 6, 9, 5])[0]
        adj = rec + timedelta(days=r.randint(3, 30)) if status not in ("PENDED", "IN_REVIEW") else None
        billed = allowed = paid = 0.0
        for ln, px in enumerate(px_by_enc[enc[0]], start=1):
            b = round(proc_map[px[2]][3] * px[3] * r.uniform(1.1, 1.8), 2)
            a = round(b * r.uniform(0.45, 0.8), 2)
            lstatus = status if status != "PARTIALLY_PAID" else r.choice(["PAID", "DENIED"])
            p = round(a * r.uniform(0.75, 0.95), 2) if lstatus == "PAID" else 0.0
            lines.append((len(lines) + 1, cid, ln, px[2], r.choice(dx_by_enc[enc[0]]), px[3], b,
                          a if lstatus != "DENIED" else 0.0, p, lstatus))
            billed += b
            allowed += a if lstatus != "DENIED" else 0.0
            paid += p
        mresp = round(max(allowed - paid, 0), 2)
        claims.append((cid, f"CLM{2025000000 + cid}", enc[1], enc[2], enc[0], member_plan[enc[1]],
                       "Institutional" if enc[5] in ("Inpatient", "Emergency") else "Professional", svc, rec, adj,
                       round(billed, 2), round(allowed, 2), round(paid, 2), mresp, status))
        if paid > 0:
            payments.append((len(payments) + 1, cid, adj, round(paid, 2), r.choice(["EFT", "EFT", "EFT", "Check"]), f"EFT{r.randint(10**8, 10**9)}"))
        if status in ("DENIED", "PARTIALLY_PAID"):
            appealed = int(r.random() < 0.35)
            denials.append((len(denials) + 1, cid, r.choices(DENIAL_REASONS, [18, 8, 6, 16, 9, 15, 7, 5, 8, 8])[0][0], adj, appealed,
                            r.choice(["OVERTURNED", "UPHELD", "PENDING"]) if appealed else None))
    ins("claims", claims)
    ins("claim_lines", lines)
    ins("claim_payments", payments)
    ins("claim_denials", denials)

    pa = []
    for i in range(1, 801):
        req = _d(r)
        st = r.choices(["APPROVED", "DENIED", "PENDING", "WITHDRAWN"], [65, 15, 15, 5])[0]
        pa.append((i, r.randint(1, len(members)), r.choice(active_prov)[0],
                   r.choice(["73721", "27447", "45378", "96413", "59400", "99285"]), req,
                   req + timedelta(days=r.randint(1, 14)) if st != "PENDING" else None, st, r.choice(["Standard", "Urgent"])))
    ins("prior_authorizations", pa)
    refs = []
    for i in range(1, 1001):
        refs.append((i, r.randint(1, len(members)), r.choice(pcp_providers)[0], r.choice(active_prov)[0],
                     r.randint(4, len(SPECIALTIES)), _d(r), r.choices(["COMPLETED", "PENDING", "SCHEDULED", "EXPIRED"], [55, 15, 20, 10])[0],
                     r.choice(["Specialist evaluation", "Second opinion", "Diagnostic workup", "Surgical consult", "Chronic care management"])))
    ins("referrals", refs)

    # ---- File operations domain (submission -> validation -> approval -> load to core) ----
    users = [(1, "asmith", "Alice Smith", "Baylor Medical Group", "Provider Data Analyst"),
             (2, "rpatel", "Raj Patel", "Sunrise Health", "Credentialing Specialist"),
             (3, "mgarcia", "Maria Garcia", "Lone Star IPA", "Network Ops Analyst"),
             (4, "jchen", "Jason Chen", "Pacific Care Partners", "Data Engineer"),
             (5, "kjohnson", "Kim Johnson", "Midwest Physicians", "Provider Data Analyst"),
             (6, "dlee", "Daniel Lee", "Atlantic Clinic Network", "Enrollment Coordinator"),
             (7, "snguyen", "Sara Nguyen", "Rocky Mountain Health", "Data Steward"),
             (8, "bwilliams", "Brian Williams", "Gulf Coast Hospitals", "Claims Analyst"),
             (9, "pkumar", "Priya Kumar", "Evergreen Medical", "Provider Data Analyst"),
             (10, "tmartin", "Tom Martin", "Capital Health System", "Network Ops Analyst"),
             (11, "lrodriguez", "Laura Rodriguez", "Desert Valley Clinic", "Credentialing Specialist"),
             (12, "ewilson", "Eric Wilson", "Northeast Care Alliance", "Data Engineer")]
    ins("submitter_users", [(u[0], u[1], u[2], u[3], u[4], f"{u[1]}@{u[3].lower().replace(' ', '')}.org", int(u[0] != 11)) for u in users])
    ins("validation_rules", VALIDATION_RULES)
    file_types = ["PROVIDER_ROSTER", "PROVIDER_DEMOGRAPHICS", "NETWORK_PARTICIPATION", "CREDENTIALING", "MEMBER_ELIGIBILITY", "CLAIMS_837"]
    # Each user has a different quality profile so the visualization agent has interesting contrasts.
    user_fail_rate = {u[0]: r.uniform(0.05, 0.45) for u in users}
    approvers = ["Nina Brooks", "Omar Haddad", "Grace Kim", "Victor Alvarez"]
    files, vresults, approvals, loads = [], [], [], []
    for i in range(1, 501):
        fid = f"FS-{2025}{i:04d}"
        u = r.choice(users)
        ftype = r.choice(file_types)
        sub_day = _d(r, date(2025, 6, 1), END)
        sub_at = _ts(r, sub_day)
        rc = r.randint(50, 25000)
        t = sub_at + timedelta(minutes=r.randint(2, 30))
        failed = r.random() < user_fail_rate[u[0]]
        in_progress_validation = sub_day > END - timedelta(days=2) and r.random() < 0.5
        failing_rules = set(r.sample([v[0] for v in VALIDATION_RULES], r.randint(1, 3))) if failed else set()
        if not in_progress_validation:
            for rule in VALIDATION_RULES:
                bad = rule[0] in failing_rules
                ec = r.randint(1, max(1, rc // 20)) if bad else 0
                vresults.append((len(vresults) + 1, fid, rule[0], t, "FAIL" if bad else "PASS", ec,
                                 f"{ec} records failed: {rule[1]}" if bad else None))
        if in_progress_validation:
            stage, status, last = "VALIDATION", "IN_PROGRESS", t
        elif failed:
            stage, status, last = "VALIDATION", "FAILED", t
        else:
            dec_at = t + timedelta(hours=r.randint(1, 72))
            decision = r.choices(["APPROVED", "REJECTED", "PENDING"], [82, 8, 10])[0]
            approvals.append((len(approvals) + 1, fid, r.choice(approvers) if decision != "PENDING" else None, decision,
                              dec_at if decision != "PENDING" else None,
                              {"APPROVED": "Validated and approved for load", "REJECTED": "Business review rejected: stale effective dates",
                               "PENDING": "Awaiting data steward review"}[decision]))
            if decision == "PENDING":
                stage, status, last = "APPROVAL", "PENDING_APPROVAL", t
            elif decision == "REJECTED":
                stage, status, last = "APPROVAL", "REJECTED", dec_at
            else:
                stage, status, last = "LOAD", "IN_PROGRESS", dec_at
                start = dec_at + timedelta(minutes=r.randint(5, 120))
                remaining = rc
                for order, sname in enumerate(["LANDING", "STAGING", "CORE"], start=1):
                    outcome = r.choices(["SUCCESS", "FAILED", "IN_PROGRESS"], [92, 5, 3])[0]
                    end = start + timedelta(minutes=r.randint(3, 90))
                    rej = r.randint(0, max(1, remaining // 100)) if outcome == "SUCCESS" else 0
                    loads.append((len(loads) + 1, fid, sname, order, outcome, start,
                                  end if outcome != "IN_PROGRESS" else None,
                                  remaining - rej if outcome == "SUCCESS" else 0, rej if outcome == "SUCCESS" else remaining))
                    last = end
                    if outcome != "SUCCESS":
                        stage, status = sname, "LOAD_FAILED" if outcome == "FAILED" else "IN_PROGRESS"
                        break
                    remaining -= rej
                    start = end
                else:
                    stage, status = "CORE", "LOADED"
        files.append((fid, f"{u[1]}_{ftype.lower()}_{sub_day:%Y%m%d}_{i}.csv", ftype, u[0], sub_at, rc,
                      max(1, rc * r.randint(1, 3) // 10), stage, status, last))
    ins("file_submissions", files)
    ins("file_validation_results", vresults)
    ins("file_approvals", approvals)
    ins("file_load_stages", loads)

    con.commit()
    con.close()
    return db_path


if __name__ == "__main__":
    from healthcare_agents.config import DB_PATH

    p = build_database(DB_PATH, force=True)
    con = sqlite3.connect(p)
    tables = [t for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        print(f"{t:35s} {con.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]:>7,}")
    print(f"\n{len(tables)} tables created at {p}")
