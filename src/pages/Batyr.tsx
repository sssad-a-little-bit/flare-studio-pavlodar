import { localUrl } from '../config/paths';
import { batyr as c, common } from '../config';
import { InquiryForm } from '../components/InquiryForm';
import { ArrowIcon, PhoneIcon } from '../components/Icons';

function Wordmark({ light = false }: { light?: boolean }) {
  return <span className={`b-wordmark${light ? ' b-wordmark-light' : ''}`}><span className="b-logo-symbol" aria-hidden="true"><i /><i /><i /></span><span>BATYR<span className="b-logo-studio">STUDIO</span></span></span>;
}

export function Batyr() {
  return <div className="batyr">
    <a className="skip-link" href="#main">{common.skip}</a>
    <header className="b-header b-container">
      <a href="#top" aria-label={c.name}><Wordmark /></a>
      <nav className="b-nav" aria-label={c.name}>{c.nav.map(item => <a key={item.href} href={item.href}>{item.label}</a>)}</nav>
      <a className="b-header-phone" href={`tel:${c.phoneHref}`}><span className="b-online-dot" aria-hidden="true" />{c.phone}<ArrowIcon diagonal /></a>
    </header>
    <main id="main" tabIndex={-1}>
      <section className="b-hero b-container" id="top" aria-labelledby="b-hero-title">
        <div className="b-hero-copy">
          <p className="b-eyebrow"><span aria-hidden="true" />{c.hero.eyebrow}</p>
          <h1 id="b-hero-title">{c.hero.first}<br />{c.hero.second}<br />{' '}<em>{c.hero.accent}</em> {c.hero.last}</h1>
          <p className="b-hero-description">{c.hero.description}</p>
          <div className="b-hero-actions"><a className="b-button" href="#inquiry">{c.hero.primary}<ArrowIcon diagonal /></a><a className="b-text-link" href={c.instagram} target="_blank" rel="noreferrer">{c.hero.secondary}<ArrowIcon diagonal /></a></div>
          <p className="b-hero-location"><span aria-hidden="true">↳</span>{c.hero.location}</p>
        </div>
        <figure className="b-hero-visual">
          <img src={c.hero.image} alt={c.hero.imageAlt} width="900" height="1000" fetchPriority="high" />
          <div className="b-visual-corner" aria-hidden="true"><span /><span /></div>
          <span className="b-vertical-type" aria-hidden="true">BATYR / STUDIO</span>
          <figcaption><span>{c.hero.imageCaption}</span><span>{c.hero.imageNote}</span></figcaption>
        </figure>
        <div className="b-hero-bottom"><span>{c.hero.bottom}</span><span aria-hidden="true">↓</span><a href={localUrl('picasso/')}>{common.otherConcept} · Picasso<ArrowIcon diagonal /></a></div>
      </section>
      <section className="b-directions" id="directions" aria-labelledby="b-directions-title">
        <div className="b-container">
          <div className="b-section-heading"><p className="b-eyebrow">{c.directions.eyebrow}</p><h2 id="b-directions-title">{c.directions.title}</h2></div>
          <div className="b-direction-list">{c.directions.items.map(item => <a className="b-direction-row" key={item.title} href="#inquiry"><span className="b-direction-tag">{item.tag}</span><h3>{item.title}</h3><p>{item.description}</p><ArrowIcon diagonal /></a>)}</div>
          <div className="b-direction-bottom"><p>{c.directions.note}</p><a className="b-text-link" href="#inquiry">{c.directions.cta}<ArrowIcon diagonal /></a></div>
        </div>
      </section>
      <section className="b-works b-container" id="works" aria-labelledby="b-works-title">
        <div className="b-works-copy"><p className="b-eyebrow">{c.works.eyebrow}</p><h2 id="b-works-title">{c.works.title}</h2><p className="b-body">{c.works.description}</p><a className="b-text-link" href={c.instagram} target="_blank" rel="noreferrer">{c.works.cta}<ArrowIcon diagonal /></a><p className="b-works-note">{c.works.note}</p></div>
        <figure className="b-material-visual"><img src={c.works.image} alt={c.works.imageAlt} width="1000" height="800" loading="lazy" /><figcaption>{c.works.caption}</figcaption><span className="b-material-plus" aria-hidden="true">+</span></figure>
      </section>
      <section className="b-process b-container" aria-labelledby="b-process-title">
        <div className="b-section-heading"><p className="b-eyebrow">{c.steps.eyebrow}</p><h2 id="b-process-title">{c.steps.title}</h2></div>
        <ol className="b-step-list">{c.steps.items.map((item, index) => <li key={item.title}><span className="b-step-index" aria-hidden="true">0{index + 1}</span><h3>{item.title}</h3><p>{item.text}</p></li>)}</ol>
      </section>
      <section className="b-inquiry" id="inquiry" aria-labelledby="batyr-inquiry-title"><div className="b-container"><InquiryForm config={c.form} phone={c.phoneHref} /></div></section>
      <section className="b-contacts b-container" id="contacts" aria-labelledby="b-contacts-title">
        <div className="b-contact-heading"><p className="b-eyebrow">{c.contacts.eyebrow}</p><h2 id="b-contacts-title">{c.contacts.title}</h2><span className="b-big-arrow" aria-hidden="true">↗</span></div>
        <div className="b-contact-details"><div><p className="b-contact-label">{c.contacts.phoneLabel}</p><a className="b-contact-phone" href={`tel:${c.phoneHref}`}>{c.phone}</a></div><div><p className="b-contact-label">{c.contacts.addressLabel}</p><p className="b-address">{c.city},<br />{c.address}</p><a className="b-text-link" href={c.mapUrl} target="_blank" rel="noreferrer" aria-label={c.contacts.mapLabel}>{c.contacts.route}<ArrowIcon diagonal /></a></div><a className="b-text-link b-instagram" href={c.instagram} target="_blank" rel="noreferrer">{c.instagramLabel}<ArrowIcon diagonal /></a><p className="b-contact-note">{c.contacts.note}</p></div>
      </section>
    </main>
    <footer className="b-footer"><div className="b-container b-footer-inner"><a href="#top" aria-label={c.name}><Wordmark light /></a><div><p>{common.demo}</p><span className="b-footer-contact">{common.flareContact}</span></div><div className="b-footer-meta"><a href={localUrl('picasso/')}>{common.otherConcept} · Picasso<ArrowIcon diagonal /></a><p>{c.contacts.checkDate}</p></div></div></footer>
    <div className="b-mobile-bar"><a className="b-mobile-call" href={`tel:${c.phoneHref}`}><PhoneIcon />{common.call}</a><a className="b-button" href="#inquiry">{c.hero.primary}<ArrowIcon diagonal /></a></div>
  </div>;
}



