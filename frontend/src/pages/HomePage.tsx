import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, AppStats } from '../api/client';
import { ErrorMessage, Loading } from '../components/Layout';

const PROCESS_STEPS = [
  {
    step: '1',
    title: 'Référencer les candidats',
    body: 'Chaque candidat est enregistré (nom, parti, statut) et relié aux identifiants externes utiles — notamment les slugs CLAIR.vote pour l’Assemblée et le Sénat.',
  },
  {
    step: '2',
    title: 'Collecter chaque nuit',
    body: 'Une ingestion automatique (GitHub Actions, 6h UTC) parcourt YouTube, les votes parlementaires, les flux RSS presse et les documents de programme. Un historique des runs est consultable.',
  },
  {
    step: '3',
    title: 'Structurer et tracer',
    body: 'Chaque élément stocke sa provenance (URL, éditeur, date de collecte). Les votes sont dédoublonnés par scrutin et chambre ; les articles par URL.',
  },
  {
    step: '4',
    title: 'Mesurer l’alignement',
    body: 'Pour chaque vote comparable, on compare la position du candidat à celle de son groupe parlementaire. Le taux de loyauté agrège ces comparaisons — ce n’est pas encore une note de cohérence multi-sources.',
  },
  {
    step: '5',
    title: 'Explorer',
    body: 'L’interface permet de parcourir candidats, groupes, partis, votes et historiques. Aucune conclusion automatique de fact-check n’est produite à ce stade.',
  },
];

const ACTIVE_SOURCES = [
  {
    name: 'CLAIR.vote',
    type: 'Votes parlementaires',
    detail:
      'Source principale pour Assemblée nationale et Sénat : position du député/sénateur, position du groupe, titre du scrutin et lien vers la source.',
  },
  {
    name: 'Open data Assemblée',
    type: 'Votes (secours)',
    detail:
      'JSON des scrutins AN utilisé si CLAIR ne renvoie rien pour un député. Couvre uniquement l’Assemblée.',
  },
  {
    name: 'YouTube Data API',
    type: 'Interviews',
    detail:
      'Recherche d’interviews, métadonnées vidéo et transcripts français lorsqu’ils sont disponibles. Nécessite une clé API.',
  },
  {
    name: 'Flux RSS presse',
    type: 'Articles',
    detail:
      'Une vingtaine de flux (Le Monde, Figaro, Libération, Mediapart, BFMTV, etc.). Filtrage par mention du nom du candidat ; extrait textuel conservé.',
  },
  {
    name: 'Programmes curated',
    type: 'Documents',
    detail:
      'URLs officielles (sites / PDF) déclarées manuellement dans le seed. Contenu téléchargé et extrait pour consultation.',
  },
];

const PLANNED_SOURCES = [
  {
    name: 'X (Twitter)',
    status: 'Non branché',
    detail:
      'Pas encore de connecteur. Une intégration utile viserait les comptes officiels déclarés, avec archivage des posts (texte, date, URL) et traçabilité de la collecte — sans scoring automatique des « likes ».',
  },
  {
    name: 'Instagram',
    status: 'Non branché',
    detail:
      'Même logique : comptes officiels, posts textuels / légendes, éventuellement stories archivées si l’API le permet. Priorité basse tant que la cohérence texte ↔ votes n’est pas en place.',
  },
  {
    name: 'Parlement européen',
    status: 'UI seule',
    detail:
      'Un onglet existe côté interface, mais aucune collecte n’est branchée. CLAIR.vote couvre aujourd’hui AN + Sénat uniquement.',
  },
];

const NEXT_STEPS = [
  {
    title: 'Extraire des positions structurées',
    body: 'À partir des transcripts YouTube et des programmes, identifier des positions thématiques (sujet + polarité) plutôt que du texte brut.',
  },
  {
    title: 'Comparer déclarations et votes',
    body: 'Passer de la loyauté au groupe à une vraie cohérence multi-sources : ce que le candidat vote vs ce qu’il dit vs ce que la presse rapporte.',
  },
  {
    title: 'Documenter la méthodologie',
    body: 'Formaliser les règles (abstention, absence, changement de groupe, plafond de votes) dans une page dédiée, versionnée avec le code.',
  },
  {
    title: 'Élargir le périmètre sources',
    body: 'Après la cohérence texte/votes : Europe, puis réseaux sociaux officiels (X, Instagram) avec comptes déclarés et provenance claire.',
  },
];

export function HomePage() {
  const [stats, setStats] = useState<AppStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  if (error) return <ErrorMessage message={error} />;
  if (!stats) return <Loading />;

  return (
    <div className="home">
      <section className="home-hero">
        <p className="home-eyebrow">Projet open source · Présidentielle 2026</p>
        <h1>Fact-Checker Présidentielle 2026</h1>
        <p className="subtitle home-lead">
          Collecte structurée des déclarations, votes et articles sur les candidats —
          pour préparer un fact-checking traçable, pas pour le remplacer.
        </p>

        <div className="stats-grid">
          <div className="stat-card">
            <span className="stat-value">{stats.candidate_count}</span>
            <span className="stat-label">Candidats suivis</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">{stats.database}</span>
            <span className="stat-label">Base de données</span>
          </div>
          <div className="stat-card">
            <span className="stat-value">
              {stats.last_ingestion_at
                ? new Date(stats.last_ingestion_at).toLocaleDateString('fr-FR')
                : '—'}
            </span>
            <span className="stat-label">Dernière ingestion</span>
          </div>
        </div>

        <div className="actions">
          <Link to="/candidates" className="btn">
            Voir les candidats
          </Link>
          <a href="#processus" className="btn btn-secondary">
            Comprendre le processus
          </a>
          <Link to="/ingestion" className="btn btn-secondary">
            Historique d&apos;ingestion
          </Link>
        </div>
      </section>

      <section id="processus" className="home-section">
        <h2>Le processus</h2>
        <p className="home-section-lead">
          De l’enregistrement d’un candidat à l’affichage des votes, le pipeline reste
          volontairement transparent : chaque donnée a une source et une date de collecte.
        </p>
        <ol className="process-list">
          {PROCESS_STEPS.map((item) => (
            <li key={item.step} className="process-item">
              <span className="process-step" aria-hidden="true">
                {item.step}
              </span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>

      <section id="sources" className="home-section">
        <h2>Sources actives</h2>
        <p className="home-section-lead">
          Uniquement des sources publiques. La provenance (URL, éditeur, moment de
          collecte) est conservée pour chaque élément.
        </p>
        <div className="source-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Source</th>
                <th>Type</th>
                <th>Rôle</th>
              </tr>
            </thead>
            <tbody>
              {ACTIVE_SOURCES.map((source) => (
                <tr key={source.name}>
                  <td>
                    <strong>{source.name}</strong>
                  </td>
                  <td>{source.type}</td>
                  <td>{source.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="notation" className="home-section">
        <h2>Notation aujourd’hui</h2>
        <p className="home-section-lead">
          Il n’existe pas encore de note globale « fiabilité » ou « cohérence
          programme ». Le seul indicateur calculé est la{' '}
          <strong>loyauté au groupe parlementaire</strong>.
        </p>
        <div className="method-grid">
          <div className="method-block">
            <h3>Par vote</h3>
            <ul>
              <li>
                Position du candidat : <em>pour</em>, <em>contre</em> ou{' '}
                <em>abstention</em>
              </li>
              <li>
                Position du groupe (fournie par CLAIR.vote) sur le même scrutin
              </li>
              <li>
                Aligné = les deux positions sont identiques ; sinon non aligné
              </li>
              <li>
                Si la position du groupe est inconnue → vote non comparable
                (exclu du taux)
              </li>
            </ul>
          </div>
          <div className="method-block">
            <h3>Taux de loyauté</h3>
            <p className="formula">
              loyauté = votes alignés ÷ votes avec position de groupe connue
            </p>
            <ul>
              <li>Affiché en pourcentage sur les fiches candidat, groupe et parti</li>
              <li>Arrondi à 3 décimales côté API, puis formaté en %</li>
              <li>
                Compteurs associés : pour / contre / abstention / total collecté
              </li>
            </ul>
          </div>
        </div>
      </section>

      <section id="coherence" className="home-section">
        <h2>Comment la cohérence des votes est jugée</h2>
        <p className="home-section-lead">
          Attention au vocabulaire : ce que l’interface montre comme « aligné » ou
          « loyauté » mesure la <strong>discipline de vote par rapport au groupe</strong>,
          pas une cohérence idéologique avec le programme ou les interviews.
        </p>
        <div className="method-grid">
          <div className="method-block">
            <h3>Ce qui est mesuré</h3>
            <ul>
              <li>Égalité stricte position candidat ↔ position du groupe</li>
              <li>Chambre par chambre (Assemblée, Sénat)</li>
              <li>Uniquement sur les scrutins où CLAIR fournit la ligne du groupe</li>
            </ul>
          </div>
          <div className="method-block">
            <h3>Ce qui ne l’est pas (encore)</h3>
            <ul>
              <li>Écart entre un vote et une promesse de campagne</li>
              <li>Contradiction entre deux déclarations médiatiques</li>
              <li>Score composite multi-sources ou « note de cohérence »</li>
            </ul>
          </div>
        </div>
        <p className="home-note">
          Ces comparaisons multi-sources font partie de la phase 2 prévue : extraction
          de positions depuis les transcripts et détection d’incohérences entre votes,
          déclarations et articles.
        </p>
      </section>

      <section id="autres-sources" className="home-section">
        <h2>Autres sources : X, Instagram, Europe…</h2>
        <p className="home-section-lead">
          Les réseaux sociaux ne sont pas encore collectés. L’approche envisagée reste
          la même que pour YouTube ou la presse : comptes officiels déclarés, contenu
          archivé avec URL et date, pas de score social.
        </p>
        <div className="source-table-wrap">
          <table className="data-table">
            <thead>
              <tr>
                <th>Piste</th>
                <th>État</th>
                <th>Comment on travaillerait</th>
              </tr>
            </thead>
            <tbody>
              {PLANNED_SOURCES.map((source) => (
                <tr key={source.name}>
                  <td>
                    <strong>{source.name}</strong>
                  </td>
                  <td>
                    <span className="badge badge-potential">{source.status}</span>
                  </td>
                  <td>{source.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="suite" className="home-section">
        <h2>Prochaines étapes prioritaires</h2>
        <p className="home-section-lead">
          Ordre suggéré pour passer d’une plateforme d’exploration à un outil de
          fact-checking utile.
        </p>
        <ol className="next-list">
          {NEXT_STEPS.map((item, index) => (
            <li key={item.title} className="next-item">
              <span className="process-step" aria-hidden="true">
                {index + 1}
              </span>
              <div>
                <h3>{item.title}</h3>
                <p>{item.body}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="actions">
          <Link to="/candidates" className="btn">
            Explorer les candidats
          </Link>
          <Link to="/groups" className="btn btn-secondary">
            Groupes parlementaires
          </Link>
          <Link to="/parties" className="btn btn-secondary">
            Partis
          </Link>
          <Link to="/manage" className="btn btn-secondary">
            Gestion
          </Link>
        </div>
      </section>
    </div>
  );
}
