import { picasso } from '../config/picasso';
import { common } from '../config';
import { InquiryForm } from '../components/InquiryForm';
import '../styles/picasso.css';

const Arrow = ({ diagonal = false }: { diagonal?: boolean }) => (
  <span aria-hidden="true">{diagonal ? '↗' : '↗'}</span>
);

export default function Picasso() {
  const c = picasso;
  return (
    <div className="picasso">
      <a className="skip-link" href="#top">{common.skip}</a>
      <header className="p-header p-container">
        <a href="#top" className="p-brand" aria-label={`${c.name} — ${c.descriptor}`}>
          <span className="p-brand-name">{c.name}<span className="p-brand-dot" aria-hidden="true" /></span>
          <span className="p-brand-description">{c.descriptor}</span>
        </a>
        <nav className="p-nav" aria-label={c.navLabel}>
          {c.nav.map(item => <a href={item.href} key={item.href}>{item.label}</a>)}
        </nav>
        <a className="p-header-contact" href="#inquiry">{c.hero.primary}<Arrow /></a>
      </header>

      <main id="top" tabIndex={-1}>
        <section className="p-hero p-container" aria-labelledby="p-hero-title">
          <div className="p-hero-copy">
            <p className="p-eyebrow"><span className="p-tiny-star" aria-hidden="true">✳</span>{c.hero.eyebrow}</p>
            <h1 id="p-hero-title">{c.hero.title.map((line, i) => <span key={line} className={i === 2 ? 'p-title-art' : undefined}>{line}{i < c.hero.title.length - 1 ? ' ' : ''}</span>)}</h1>
            <p className="p-hero-description">{c.hero.text}</p>
            <div className="p-hero-actions">
              <a className="p-button" href="#inquiry">{c.hero.primary}<Arrow /></a>
              <a className="p-secondary" href={c.instagram} target="_blank" rel="noreferrer">{c.hero.secondary}<small>{c.hero.externalNote}</small></a>
            </div>
          </div>
          <div className="p-hero-art">
            <span className="p-art-note">{c.hero.aside}</span>
            <span className="p-hero-spark" aria-hidden="true">✳</span>
            <figure className="p-main-sheet">
              <img src={c.hero.image} alt={c.hero.imageAlt} width="720" height="860" fetchPriority="high" />
              <figcaption><span>{c.hero.caption}</span><span>{c.hero.captionDetail}</span></figcaption>
            </figure>
            <span className="p-paper-tag" aria-hidden="true">{c.name}</span>
          </div>
          <p className="p-scroll"><span aria-hidden="true">↓</span>{c.hero.scroll}</p>
        </section>

        <section id="atmosphere" className="p-atmosphere p-container" aria-labelledby="p-atmosphere-title">
          <div className="p-atmosphere-art">
            <figure className="p-study-sheet">
              <img src={c.atmosphere.image} alt={c.atmosphere.imageAlt} width="650" height="690" loading="lazy" />
              <figcaption>{c.atmosphere.caption}</figcaption>
            </figure>
            <span className="p-hand-note">{c.atmosphere.note}<span aria-hidden="true">⤴</span></span>
          </div>
          <div className="p-atmosphere-copy">
            <p className="p-eyebrow">{c.atmosphere.eyebrow}</p>
            <h2 id="p-atmosphere-title">{c.atmosphere.title}</h2>
            <p className="p-body">{c.atmosphere.text}</p>
            <div className="p-instagram-note">
              <span className="p-line-star" aria-hidden="true">✳</span>
              <p>{c.atmosphere.workText}</p>
              <a className="p-text-link" href={c.instagram} target="_blank" rel="noreferrer">{c.atmosphere.workLink}<Arrow diagonal /></a>
            </div>
          </div>
        </section>

        <section id="how-to-choose" className="p-steps" aria-labelledby="p-steps-title">
          <div className="p-container">
            <div className="p-section-heading">
              <div><p className="p-eyebrow">{c.steps.eyebrow}</p><h2 id="p-steps-title">{c.steps.title}</h2></div>
              <p>{c.steps.intro}</p>
            </div>
            <ol className="p-step-list">
              {c.steps.items.map(item => <li key={item.number}><span className="p-step-number">{item.number}</span><h3>{item.title}</h3><p>{item.text}</p></li>)}
            </ol>
          </div>
        </section>

        <section id="inquiry" className="p-inquiry p-container" aria-labelledby="picasso-inquiry-title">
          <div className="p-inquiry-decoration" aria-hidden="true"><span>✳</span><i /><i /><i /></div>
          <InquiryForm config={c.form} phone={c.phoneHref} />
        </section>

        <section id="contacts" className="p-contacts" aria-labelledby="p-contacts-title">
          <div className="p-container p-contacts-layout">
            <div className="p-contacts-heading"><p className="p-eyebrow">{c.contacts.eyebrow}</p><h2 id="p-contacts-title">{c.contacts.title}</h2><span className="p-contact-squiggle" aria-hidden="true">〰</span></div>
            <div className="p-contact-details">
              <div><p className="p-contact-label">{c.contacts.locationLabel}</p><p className="p-address">{c.city}<br />{c.address}</p><a className="p-text-link" href={c.map} target="_blank" rel="noreferrer">{c.contacts.mapLabel}<Arrow diagonal /></a></div>
              <div><p className="p-contact-label">{c.contacts.phoneLabel}</p><a className="p-phone" href={`tel:${c.phoneHref}`}>{c.phone}</a></div>
              <div><p className="p-contact-label">{c.contacts.instagramLabel}</p><a className="p-text-link p-instagram-handle" href={c.instagram} target="_blank" rel="noreferrer">{c.instagramLabel}<Arrow diagonal /></a></div>
              <p className="p-contact-note">{c.contacts.note}</p>
            </div>
          </div>
        </section>
      </main>

      <footer className="p-footer p-container">
        <span className="p-footer-name">{c.name}<span aria-hidden="true">.</span></span>
        <div><p>{c.footer.concept}</p><span className="p-footer-contact">{c.footer.contact}</span></div>
        <div className="p-footer-meta"><a href={c.switchHref}>{c.switchLabel}<Arrow diagonal /></a><p>{c.footer.date}</p></div>
      </footer>
      <div className="p-mobile-bar"><a className="p-button" href="#inquiry">{c.mobileAction}<Arrow /></a></div>
    </div>
  );
}



