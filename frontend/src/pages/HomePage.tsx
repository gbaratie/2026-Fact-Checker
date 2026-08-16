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
    title: 'Structurer les positions',
    body: 'Les déclarations sont saisies comme claims (thème + stance + citation + source). Les votes peuvent être tagués par les mêmes thèmes pour permettre une comparaison.',
  },
  {
    step: '5',
    title: 'Comparer et explorer',
    body: 'Deux indicateurs : loyauté au groupe parlementaire, et cohérence déclaration ↔ vote par thème. Pas de score global automatique ni de fact-check qui remplace un humain.',
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
    title: 'Curater un premier corpus de claims',
    body: 'Saisir manuellement 20–50 positions sur quelques candidats (programme + interviews), et taguer les votes associés, pour valider la taxonomie.',
  },
  {
    title: 'Extraction assistée (LLM)',
    body: 'Proposer des claims depuis transcripts et programmes, avec revue humaine obligatoire avant publication.',
  },
  {
    title: 'Enrichir les preuves',
    body: 'Lier systématiquement chaque claim à une interview, un document de programme ou un article déjà collecté.',
  },
  {
    title: 'Élargir les sources',
    body: 'Parlement européen, puis comptes officiels X / Instagram — seulement après un volume suffisant de claims validés.',
  },
];

function HomeStats({
  stats,
  error,
}: {
  stats: AppStats | null;
  error: string | null;
}) {
  if (error) {
    return (
      <div className="stats-live" role="status">
        <ErrorMessage message={error} />
      </div>
    );
  }

  if (!stats) {
    return (
      <div className="stats-grid stats-grid--pending" aria-busy="true">
        {['Candidats suivis', 'Base de données', 'Dernière ingestion'].map((label) => (
          <div key={label} className="stat-card stat-card--pending">
            <span className="stat-value stat-value--pending">…</span>
            <span className="stat-label">{label}</span>
          </div>
        ))}
        <div className="stats-loading-hint">
          <Loading />
          <p className="stats-loading-note">
            L’API peut mettre quelques dizaines de secondes à se réveiller (Render free).
          </p>
        </div>
      </div>
    );
  }

  return (
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
  );
}

export function HomePage() {
  const [stats, setStats] = useState<AppStats | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then(setStats)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="home">
      <section className="home-hero">
        <p className="home-eyebrow">Projet open source · Présidentielle 2026</p>
        <h1>Fact-Checker Présidentielle 2026</h1>
        <p className="subtitle home-lead">
          Collecte structurée des déclarations, votes et articles sur les candidats —
          pour préparer un fact-checking traçable, pas pour le remplacer.
        </p>

        <HomeStats stats={stats} error={error} />

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
          Pas de note globale « fiabilité ». Deux indicateurs distincts coexistent :
          la <strong>loyauté au groupe</strong> et la{' '}
          <strong>cohérence déclaration ↔ vote</strong> par thème.
        </p>
        <div className="method-grid">
          <div className="method-block">
            <h3>Loyauté au groupe</h3>
            <p className="formula">
              loyauté = votes alignés ÷ votes avec position de groupe connue
            </p>
            <ul>
              <li>Comparaison position candidat ↔ ligne du groupe (CLAIR)</li>
              <li>Hors scope : programme, interviews, presse</li>
            </ul>
          </div>
          <div className="method-block">
            <h3>Positions structurées (claims)</h3>
            <ul>
              <li>Thème (immigration, fiscalité, énergie…)</li>
              <li>Stance : pour / contre / nuance / inconnu</li>
              <li>Résumé + citation + URL ou preuve liée</li>
              <li>Saisie manuelle via l’onglet Positions (secret admin)</li>
            </ul>
          </div>
        </div>
      </section>

      <section id="coherence" className="home-section">
        <h2>Comment la cohérence est jugée</h2>
        <p className="home-section-lead">
          Sur chaque thème où existent à la fois des claims et des votes tagués, on
          compare les polarités <em>pour</em> / <em>contre</em>.
        </p>
        <div className="method-grid">
          <div className="method-block">
            <h3>Statuts</h3>
            <ul>
              <li>
                <strong>Aligné</strong> — même polarité des deux côtés
              </li>
              <li>
                <strong>Contradiction</strong> — pour d’un côté, contre de l’autre
              </li>
              <li>
                <strong>Mixte</strong> — polarités multiples ou partiellement
                chevauchantes
              </li>
              <li>
                <strong>Déclaration seule / vote seul</strong> — pas encore comparable
              </li>
            </ul>
          </div>
          <div className="method-block">
            <h3>Limites assumées</h3>
            <ul>
              <li>Pas de score composite automatique</li>
              <li>Abstention et « nuance » ne créent pas de contradiction</li>
              <li>Les votes non tagués sont ignorés par la cohérence thématique</li>
              <li>L’extraction LLM n’est pas encore branchée</li>
            </ul>
          </div>
        </div>
        <p className="home-note">
          Les tables <code>topics</code>, <code>claims</code> et{' '}
          <code>vote_topics</code> sont en place : on peut curater maintenant, puis
          automatiser l’extraction ensuite.
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
