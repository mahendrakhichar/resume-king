export interface ContactInfo {
  name?: string;
  email?: string;
  phone?: string;
  linkedin?: string;
  github?: string;
  portfolio?: string;
  location?: string;
}

export interface Experience {
  company: string;
  title: string;
  location?: string;
  start_date?: string;
  end_date?: string;
  is_current: boolean;
  bullets: string[];
}

export interface Project {
  name: string;
  description?: string;
  technologies: string[];
  url?: string;
  bullets: string[];
}

export interface Education {
  institution: string;
  degree: string;
  field_of_study?: string;
  start_date?: string;
  end_date?: string;
  gpa?: string;
  highlights: string[];
}

export interface Certification {
  name: string;
  issuer?: string;
  date?: string;
  url?: string;
}

export interface ParsedResumeData {
  contact: ContactInfo;
  summary?: string;
  skills: string[];
  experience: Experience[];
  education: Education[];
  projects: Project[];
  certifications?: Certification[];
  achievements?: string[];
  languages?: string[];
}

export interface ResumeListItem {
  id: string;
  original_filename: string;
  file_type: string;
  version: number;
  is_tailored: boolean;
  created_at: string;
}

export interface ResumeDetail {
  id: string;
  original_filename: string;
  file_type: string;
  parsed_data?: ParsedResumeData;
  raw_text?: string;
  version: number;
  is_tailored: boolean;
  parent_id?: string;
  created_at: string;
}
