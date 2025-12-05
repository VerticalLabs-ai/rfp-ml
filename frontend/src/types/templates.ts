export interface SectionTemplate {
  id: string
  name: string
  description: string
  category: 'executive' | 'technical' | 'management' | 'pricing' | 'compliance' | 'general'
  sectionType: string
  content: string
  variables: TemplateVariable[]
  tags: string[]
  isBoilerplate: boolean
  createdAt: string
  updatedAt: string
}

export interface TemplateVariable {
  key: string
  label: string
  defaultValue: string
  required: boolean
}

export interface TemplateCategory {
  id: string
  name: string
  icon: string
  description: string
}

export const TEMPLATE_CATEGORIES: TemplateCategory[] = [
  {
    id: 'executive',
    name: 'Executive Summary',
    icon: 'FileText',
    description: 'Opening statements and value propositions',
  },
  {
    id: 'technical',
    name: 'Technical Approach',
    icon: 'Code',
    description: 'Methodology and implementation details',
  },
  {
    id: 'management',
    name: 'Management',
    icon: 'Users',
    description: 'Team structure and project management',
  },
  {
    id: 'pricing',
    name: 'Pricing',
    icon: 'DollarSign',
    description: 'Cost narratives and pricing justification',
  },
  {
    id: 'compliance',
    name: 'Compliance',
    icon: 'Shield',
    description: 'Regulatory and contractual compliance',
  },
  {
    id: 'general',
    name: 'General',
    icon: 'Folder',
    description: 'Reusable boilerplate content',
  },
]

// Default templates for initial setup
export const DEFAULT_TEMPLATES: Omit<SectionTemplate, 'id' | 'createdAt' | 'updatedAt'>[] = [
  {
    name: 'Standard Executive Summary',
    description: 'Professional executive summary with value proposition',
    category: 'executive',
    sectionType: 'executive_summary',
    content: `## Executive Summary

{{company_name}} is pleased to submit this proposal in response to {{rfp_title}}. With {{years_experience}} years of experience in {{industry}}, we are uniquely positioned to deliver exceptional results.

### Our Understanding
We understand the critical importance of this initiative and have carefully analyzed the requirements to develop a comprehensive solution that addresses your needs.

### Value Proposition
- Proven track record with similar engagements
- Dedicated team of certified professionals
- Innovative approach combining best practices with cutting-edge technology
- Commitment to exceeding performance standards

### Why {{company_name}}
Our approach is built on a foundation of {{core_competency}}, ensuring that we deliver measurable results on time and within budget.`,
    variables: [
      { key: 'company_name', label: 'Company Name', defaultValue: '', required: true },
      { key: 'rfp_title', label: 'RFP Title', defaultValue: '', required: true },
      { key: 'years_experience', label: 'Years of Experience', defaultValue: '15', required: false },
      { key: 'industry', label: 'Industry', defaultValue: 'government contracting', required: false },
      { key: 'core_competency', label: 'Core Competency', defaultValue: 'technical excellence', required: false },
    ],
    tags: ['standard', 'federal', 'professional'],
    isBoilerplate: false,
  },
  {
    name: 'Technical Methodology',
    description: 'Standard technical approach with phased implementation',
    category: 'technical',
    sectionType: 'technical_approach',
    content: `## Technical Approach

### Methodology Overview
Our technical approach follows industry-recognized methodologies adapted for {{agency_type}} requirements. We employ an iterative, risk-managed approach that ensures continuous delivery of value.

### Phase 1: Discovery & Planning
- Requirements validation and gap analysis
- Stakeholder interviews and workshops
- Technical architecture design
- Risk assessment and mitigation planning

### Phase 2: Development & Implementation
- Agile development sprints with bi-weekly demonstrations
- Continuous integration and automated testing
- Security and compliance validation
- User acceptance testing

### Phase 3: Deployment & Transition
- Staged rollout with pilot programs
- Knowledge transfer and documentation
- Training delivery
- Post-deployment support

### Quality Assurance
All deliverables undergo rigorous quality checks aligned with {{quality_standard}} standards.`,
    variables: [
      { key: 'agency_type', label: 'Agency Type', defaultValue: 'federal', required: false },
      { key: 'quality_standard', label: 'Quality Standard', defaultValue: 'ISO 9001', required: false },
    ],
    tags: ['technical', 'methodology', 'agile'],
    isBoilerplate: false,
  },
  {
    name: 'Company Capabilities',
    description: 'Standard company qualifications boilerplate',
    category: 'general',
    sectionType: 'company_qualifications',
    content: `## Company Qualifications

### About {{company_name}}
{{company_name}} is a {{company_type}} specializing in {{specialization}}. Established in {{established_year}}, we have grown to {{employee_count}} employees serving clients across {{service_regions}}.

### Certifications & Clearances
{{#certifications}}
- {{.}}
{{/certifications}}

### Contract Vehicles
{{#contract_vehicles}}
- {{.}}
{{/contract_vehicles}}

### Core Competencies
{{#competencies}}
- {{.}}
{{/competencies}}`,
    variables: [
      { key: 'company_name', label: 'Company Name', defaultValue: '', required: true },
      { key: 'company_type', label: 'Company Type', defaultValue: 'small business', required: false },
      { key: 'specialization', label: 'Specialization', defaultValue: 'IT services', required: false },
      { key: 'established_year', label: 'Year Established', defaultValue: '2010', required: false },
      { key: 'employee_count', label: 'Employee Count', defaultValue: '50', required: false },
      { key: 'service_regions', label: 'Service Regions', defaultValue: 'the federal government', required: false },
    ],
    tags: ['boilerplate', 'qualifications', 'company'],
    isBoilerplate: true,
  },
]
