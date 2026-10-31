import { useRef, useState } from 'react';
import type { FormEvent } from 'react';
import type { InquiryConfig } from '../config/types';
import { common } from '../config';
import { ArrowIcon, PhoneIcon, CopyIcon } from './Icons';

export function InquiryForm({ config, phone }: { config: InquiryConfig; phone: string }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [summary, setSummary] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const summaryRef = useRef<HTMLTextAreaElement>(null);
  const formRef = useRef<HTMLFormElement>(null);

  function prepare(event: FormEvent) {
    event.preventDefault();
    const nextErrors: Record<string, string> = {};
    for (const field of config.fields) {
      const value = values[field.name]?.trim() || '';
      if (field.required && !value) nextErrors[field.name] = common.emptyError;
      if (field.type === 'year' && value && (!/^\d{4}$/.test(value) || Number(value) < 1900 || Number(value) > 2027)) nextErrors[field.name] = common.yearError;
    }
    setErrors(nextErrors);
    setStatus('');
    if (Object.keys(nextErrors).length) {
      formRef.current?.querySelector<HTMLElement>(`[name="${Object.keys(nextErrors)[0]}"]`)?.focus();
      return;
    }
    const lines = config.lines.filter(line => values[line.field]?.trim()).map(line => `${line.prefix}: ${values[line.field].trim()}`);
    setSummary([config.greeting, '', ...lines, '', config.closing].filter(line => line !== undefined).join('\n').trim());
    requestAnimationFrame(() => summaryRef.current?.focus());
  }

  async function copy() {
    if (!summary?.trim()) { setStatus(common.emptySummary); summaryRef.current?.focus(); return; }
    try {
      await navigator.clipboard.writeText(summary);
      setStatus(common.copied);
    } catch {
      summaryRef.current?.focus();
      summaryRef.current?.select();
      setStatus(common.copyFailed);
    }
  }

  return <div className="inquiry-form" id={config.id}>
    <div className="form-section-heading">
      <p className="form-eyebrow">{config.eyebrow}</p>
      <h2 id={`${config.id}-title`}>{config.title}</h2>
      <p>{config.description}</p>
    </div>
    <form ref={formRef} onSubmit={prepare} noValidate>
      <div className="form-grid">
        {config.fields.map(field => {
          const id = `${config.id}-${field.name}`;
          const shared = {
            id, name: field.name,
            value: values[field.name] || '',
            onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
              setValues(current => ({ ...current, [field.name]: event.target.value }));
              if (errors[field.name]) setErrors(current => ({ ...current, [field.name]: '' }));
              setStatus('');
            },
            required: field.required,
            'aria-invalid': !!errors[field.name],
            'aria-describedby': errors[field.name] ? `${id}-error` : undefined,
            className: 'form-input',
          };
          return <div className={`field ${field.type === 'textarea' ? 'field-wide' : ''}`} key={field.name}>
            <label className="form-label" htmlFor={id}>{field.label}{!field.required && <span> · {common.optional}</span>}</label>
            {field.type === 'textarea' ? <textarea {...shared} rows={3} maxLength={field.maxLength} placeholder={field.placeholder} />
              : field.type === 'select' ? <select {...shared}><option value="" disabled>{common.selectDirection}</option>{field.options?.map(option => <option key={option}>{option}</option>)}</select>
              : <input {...shared} type="text" inputMode={field.type === 'year' ? 'numeric' : 'text'} maxLength={field.maxLength ?? 150} placeholder={field.placeholder} />}
            {errors[field.name] && <p className="form-error" id={`${id}-error`}>{errors[field.name]}</p>}
          </div>;
        })}
      </div>
      <button className="form-submit" type="submit">{summary === null ? config.submitLabel : common.regenerate}<ArrowIcon /></button>
      <p className="form-note">{common.localOnly}</p>
    </form>
    {summary !== null && <div className="form-summary">
      <h3>{common.summaryTitle}</h3>
      <p>{common.summaryHelp}</p>
      <label className="form-label" htmlFor={`${config.id}-summary`}>{common.summaryLabel}</label>
      <textarea ref={summaryRef} id={`${config.id}-summary`} className="form-summary-text form-input" rows={10} maxLength={5000} value={summary} onChange={event => { setSummary(event.target.value); setStatus(''); }} />
      <div className="form-actions">
        <button type="button" className="form-copy" onClick={copy}><CopyIcon />{common.copy}</button>
        <a className="form-call" href={`tel:${phone}`}><PhoneIcon />{common.call}</a>
      </div>
      <p className="form-status" role="status" aria-live="polite">{status}</p>
    </div>}
  </div>;
}


