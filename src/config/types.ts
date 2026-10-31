export type FieldConfig = {
  name: string;
  label: string;
  placeholder?: string;
  required?: boolean;
  type?: 'text' | 'textarea' | 'select' | 'year';
  options?: string[];
  maxLength?: number;
};
export type InquiryConfig = {
  id: string;
  eyebrow: string;
  title: string;
  description: string;
  fields: FieldConfig[];
  submitLabel: string;
  greeting: string;
  lines: { field: string; prefix: string }[];
  closing?: string;
};
export type GalleryItem = { src: string; alt: string; caption: string; permission: string };
