# PT Insights OS — Taxonomy

3-level PT industry taxonomy for community content classification.

## Structure

**L1 Domain** → **L2 Subdomain** → **L3 Tags**

## Domains

### Clinical Practice
- **Treatment Approaches**: manual_therapy, exercise_prescription, modalities, dry_needling, telehealth_delivery
- **Patient Outcomes**: outcome_measures, patient_satisfaction, functional_improvement, discharge_planning
- **Specialization**: orthopedic, neurological, pediatric, geriatric, sports_medicine, pelvic_health, hand_therapy

### Reimbursement
- **Insurance Contracting**: rate_negotiation, contract_terms, payer_mix, fee_schedule
- **Billing & Coding**: cpt_codes, modifier_usage, claim_denials, authorization, billing_compliance
- **Payer Relations**: medicare, medicaid, commercial_insurance, workers_comp, auto_insurance

### Sales & Marketing
- **Patient Acquisition**: referral_building, physician_relations, direct_access, community_outreach
- **Digital Marketing**: social_media, website_seo, online_reviews, content_marketing
- **Branding**: practice_differentiation, niche_positioning, reputation_management

### Operations
- **Practice Management**: scheduling_optimization, patient_flow, inventory_management, facility_management
- **Financial Management**: revenue_cycle, cash_flow, budgeting, profitability
- **Quality Improvement**: process_improvement, patient_safety, compliance_audits

### Staffing
- **Hiring**: recruitment, job_postings, interview_process, compensation_benchmarks
- **Retention**: employee_satisfaction, benefits_packages, career_development, mentorship
- **Workforce Planning**: staffing_ratios, productivity_standards, pta_utilization, travel_pt, prn_staffing

### Legal & Compliance
- **Regulatory**: state_practice_act, direct_access_laws, hipaa, osha
- **Business Legal**: employment_law, malpractice, entity_structure, non_compete
- **Credentialing**: provider_enrollment, pecos, caqh, npi_management

### Documentation
- **Clinical Documentation**: eval_documentation, daily_notes, progress_notes, discharge_summaries
- **Compliance Documentation**: medical_necessity, audit_readiness, documentation_standards

### EMR & Technology
- **EMR Systems**: webpt, clinicient, net_health, prompt, system_comparison
- **Practice Technology**: telehealth_platforms, patient_portal, scheduling_software, billing_software, exercise_apps

### Burnout & Wellness
- **Burnout Signs**: workload_stress, documentation_burden, productivity_pressure, compassion_fatigue
- **Wellness Strategies**: work_life_balance, boundary_setting, career_change, self_care

### Negotiation
- **Payer Negotiation**: rate_increase, contract_leverage, outcomes_data, collective_bargaining
- **Salary Negotiation**: salary_benchmarks, benefits_negotiation, promotion_strategy

### Scaling & Growth
- **Practice Ownership**: startup_planning, buying_practice, partnership_models, exit_strategy
- **Expansion**: multi_location, service_diversification, cash_based_transition, mobile_practice
- **Business Models**: cash_pay, hybrid_model, concierge_pt, wellness_programs

### Referrals
- **Physician Referrals**: md_relationships, referral_tracking, communication_strategies
- **Patient Referrals**: word_of_mouth, referral_programs, testimonials

### Contracting
- **Payer Contracts**: contract_review, termination_clauses, rate_structures, network_participation
- **Vendor Contracts**: emr_contracts, lease_agreements, service_agreements

## Tagging Approach

1. **Rule-based** (deterministic): Keyword regex patterns match first with confidence 1.0
2. **Embedding similarity** (backstop): TF-IDF cosine similarity when rules find < 2 tags
3. **LLM classifier** (optional): Behind `ENABLE_LLM_TAGGER` feature flag, OFF by default

Full rule definitions: `src/pt_insights_os/taxonomy/rules.py`
Taxonomy YAML: `src/pt_insights_os/taxonomy/taxonomy.yaml`
