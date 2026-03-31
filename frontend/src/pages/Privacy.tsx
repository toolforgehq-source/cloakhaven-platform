import { Link } from "react-router-dom";
import { Shield } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export default function Privacy() {
  useDocumentTitle("Privacy Policy");
  return (
    <div className="min-h-screen bg-slate-950">
      <Navbar
        links={[
          { to: "/search", label: "Search" },
          { to: "/pricing", label: "Pricing" },
          { to: "/login", label: "Log in" },
        ]}
        rightContent={
          <Link to="/register" className="bg-indigo-500 hover:bg-indigo-600 text-white text-sm px-4 py-2 rounded-lg transition font-medium">
            Get Your Score
          </Link>
        }
        variant="public"
      />

      <main className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="w-8 h-8 text-indigo-400" />
          <h1 className="text-3xl font-bold text-white">Privacy Policy</h1>
        </div>
        <p className="text-sm text-slate-500 mb-8">Last updated: March 31, 2026</p>

        <div className="prose prose-invert prose-sm max-w-none space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Introduction</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven (&ldquo;we,&rdquo; &ldquo;our,&rdquo; or &ldquo;us&rdquo;) operates the cloakhaven.com website and related services.
              This Privacy Policy explains how we collect, use, disclose, and safeguard information when
              you use our platform &mdash; whether you are a registered user, an unauthenticated visitor, or a
              person whose publicly available information appears in our search results (&ldquo;data subject&rdquo;).
            </p>
            <p className="text-slate-400 leading-relaxed mt-3">
              We are committed to transparency. Because our service analyzes publicly available information
              about real people &mdash; including people who have not signed up &mdash; this policy describes how we
              handle data for all categories of individuals.
            </p>
          </section>

          <section className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-amber-400 mb-3">Important: FCRA Disclaimer</h2>
            <p className="text-slate-300 leading-relaxed font-medium">
              Cloak Haven is <strong>NOT</strong> a consumer reporting agency as defined by the Fair Credit Reporting
              Act (FCRA), 15 U.S.C. &sect; 1681 et seq. Our scores and reports are <strong>not consumer reports</strong> and
              must not be used as a factor in determining eligibility for credit, insurance, employment, housing,
              or any other purpose governed by the FCRA. See our{" "}
              <Link to="/terms" className="text-indigo-400 hover:underline">Terms of Service</Link> for full details.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. What We Scan and Why</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven generates digital reputation scores by analyzing publicly available information.
              When a search is performed &mdash; by a registered user or an unauthenticated visitor &mdash; we query
              the following categories of public data sources:
            </p>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">2.1 Public Data Sources We Use</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">Web search results</strong> &mdash; via SerpAPI (Google Search). News articles, blog posts, press mentions, and other publicly indexed web pages.</li>
              <li><strong className="text-slate-300">Social media mentions</strong> &mdash; via Twitter/X API. Public tweets, mentions, and profile information.</li>
              <li><strong className="text-slate-300">Video content</strong> &mdash; via YouTube Data API. Public videos, channel information, and associated metadata.</li>
              <li><strong className="text-slate-300">Identity enrichment</strong> &mdash; via PeopleDataLabs. Public professional information (job titles, companies, locations) used to disambiguate common names.</li>
              <li><strong className="text-slate-300">Public records</strong> &mdash; via SerpAPI (Google Search). Court records, legal filings, and government databases that are publicly accessible.</li>
              <li><strong className="text-slate-300">Academic and professional content</strong> &mdash; publicly available publications, conference talks, and professional contributions.</li>
            </ul>
            <p className="text-slate-400 leading-relaxed mt-3">
              We do <strong className="text-white">not</strong> access private messages, password-protected accounts, non-public
              social media posts, financial records, medical records, or any information that requires
              authentication to access. All data sources are publicly available to anyone with an internet connection.
            </p>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">2.2 How We Process Results</h3>
            <p className="text-slate-400 leading-relaxed">
              Raw search results are processed through an AI-powered pipeline that:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">Disambiguates identity</strong> &mdash; uses contextual signals (location, profession, known associations) to determine whether a result is about the correct person</li>
              <li><strong className="text-slate-300">Classifies content</strong> &mdash; categorizes each finding (e.g., professional achievement, legal issue, community involvement, negative press)</li>
              <li><strong className="text-slate-300">Assesses severity and recency</strong> &mdash; weights findings by how recent they are and how widely they were distributed</li>
              <li><strong className="text-slate-300">Cross-references for corroboration</strong> &mdash; findings mentioned by multiple independent sources receive higher confidence</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. Information We Collect</h2>

            <h3 className="text-lg font-medium text-slate-300 mb-2">3.1 From Registered Users</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Account registration data (name, email, hashed password)</li>
              <li>Social media account connections (via OAuth &mdash; we only access public profile data)</li>
              <li>Data archive uploads (processed in memory and <strong className="text-white">immediately deleted</strong> &mdash; zero retention of raw uploads)</li>
              <li>Dispute submissions and supporting evidence</li>
              <li>Payment information (processed securely by Stripe &mdash; we never store card numbers)</li>
              <li>Profile visibility preferences (public or private)</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">3.2 From Unauthenticated Visitors</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>IP address (used solely for rate limiting and abuse prevention &mdash; not stored permanently)</li>
              <li>Search queries (the names searched are used to generate and cache public profiles)</li>
              <li>Basic usage data (pages visited, timestamp)</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">3.3 About Data Subjects (People Who Are Searched)</h3>
            <p className="text-slate-400 leading-relaxed">
              When someone is searched on Cloak Haven, we create a public profile containing:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>The person&apos;s name as entered by the searcher</li>
              <li>A generated username based on the name</li>
              <li>An aggregate reputation score (0&ndash;850 scale)</li>
              <li>Classified findings from public sources (category, severity, source URL, confidence level)</li>
              <li>Score accuracy percentage and breakdown by category</li>
            </ul>
            <p className="text-slate-400 leading-relaxed mt-3">
              This information is derived entirely from publicly available sources. We do not create profiles
              using non-public information. Any person can claim and manage their profile &mdash; see Section 7.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. How We Use Information</h2>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>To calculate and maintain reputation scores based on public data</li>
              <li>To provide detailed findings and their sources</li>
              <li>To process disputes and update scores accordingly</li>
              <li>To prevent abuse (rate limiting, daily scan caps, bot detection)</li>
              <li>To send transactional emails (verification, score updates, dispute notifications)</li>
              <li>To process payments through Stripe</li>
              <li>To improve scoring accuracy and disambiguation algorithms</li>
              <li>To comply with legal obligations</li>
            </ul>
            <p className="text-slate-400 leading-relaxed mt-3">
              We do <strong className="text-white">not</strong> sell personal information. We do <strong className="text-white">not</strong> use
              personal information for advertising. We do <strong className="text-white">not</strong> share individual-level data with
              third parties except as described in Section 6.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Data Retention</h2>

            <h3 className="text-lg font-medium text-slate-300 mb-2">5.1 Registered User Data</h3>
            <p className="text-slate-400 leading-relaxed">
              Account data is retained for the life of your account. You may delete your account at any time,
              which will permanently remove your registration data, connected accounts, and score history.
              Dispute records may be retained for up to 2 years for legal compliance purposes.
            </p>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">5.2 Public Profile Data</h3>
            <p className="text-slate-400 leading-relaxed">
              Cached public profiles are refreshed periodically (approximately every 30 days) and may be
              removed upon request (see Section 7). Stale profiles that have not been accessed in 90 days
              may be automatically purged.
            </p>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">5.3 Upload Data (Zero Retention)</h3>
            <p className="text-slate-400 leading-relaxed">
              When you upload data archives (Instagram, TikTok, Facebook, LinkedIn exports), the raw files are
              processed in memory to generate classified findings, then <strong className="text-white">immediately and permanently
              deleted</strong>. We never store, copy, or back up your original data exports. Only the classified
              findings (category, severity, score impact) are retained &mdash; never the raw content itself.
            </p>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">5.4 Rate Limiting Data</h3>
            <p className="text-slate-400 leading-relaxed">
              IP addresses used for rate limiting and abuse prevention are stored in a local database and
              automatically purged after 48 hours. Daily scan logs (which track the number of unique names
              scanned per IP) are purged after 2 days.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. Information Sharing</h2>
            <p className="text-slate-400 leading-relaxed">
              We share information only in the following limited circumstances:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">Public profiles</strong> &mdash; by design, public profile scores and findings are visible to anyone who searches for that name. This is the core function of the service.</li>
              <li><strong className="text-slate-300">Partner API</strong> &mdash; approved partners may access scores through our API, subject to rate limits and usage agreements. Partners agree not to use scores for FCRA-regulated purposes.</li>
              <li><strong className="text-slate-300">Payment processing</strong> &mdash; Stripe processes payments on our behalf. We never transmit or store credit card numbers.</li>
              <li><strong className="text-slate-300">Error monitoring</strong> &mdash; we use Sentry for application error tracking. Error reports may contain request metadata but not score data or personal information.</li>
              <li><strong className="text-slate-300">Legal compliance</strong> &mdash; we may disclose information if required by law, subpoena, court order, or to protect our legal rights.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Your Rights &mdash; Opt-Out, Removal, and Correction</h2>

            <h3 className="text-lg font-medium text-slate-300 mb-2">7.1 For Data Subjects (People Who Appear in Search Results)</h3>
            <p className="text-slate-400 leading-relaxed">
              If you find a profile about yourself on Cloak Haven, you have the following rights:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">Claim your profile</strong> &mdash; create an account and verify your identity to take control of your profile. Claimed profiles can be set to private, hiding them from public search results.</li>
              <li><strong className="text-slate-300">Request removal</strong> &mdash; email <a href="mailto:privacy@cloakhaven.com" className="text-indigo-400 hover:underline">privacy@cloakhaven.com</a> with &ldquo;Profile Removal Request&rdquo; in the subject line. Include the name as it appears on the profile. We will process removal requests within 30 business days.</li>
              <li><strong className="text-slate-300">Dispute findings</strong> &mdash; if any finding is inaccurate, outdated, or misattributed (belongs to a different person with the same name), you can dispute it. Claimed profiles can dispute directly; unclaimed profile subjects can email us.</li>
              <li><strong className="text-slate-300">Set profile to private</strong> &mdash; after claiming your profile, you can set it to private so it no longer appears in search results.</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">7.2 For Registered Users</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Access and download all data we hold about you</li>
              <li>Correct inaccurate information</li>
              <li>Delete your account and all associated data</li>
              <li>Toggle your profile between public and private at any time</li>
              <li>Dispute any individual finding</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">7.3 CCPA (California Residents)</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Right to know what personal information we collect and how it is used</li>
              <li>Right to delete your personal information</li>
              <li>Right to opt-out of the sale of personal information (<strong className="text-white">we do not sell data</strong>)</li>
              <li>Right to non-discrimination for exercising your rights</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">7.4 GDPR (EU/EEA Residents)</h3>
            <p className="text-slate-400 leading-relaxed">
              Our legal basis for processing publicly available data is legitimate interest (Article 6(1)(f) GDPR) &mdash;
              specifically, the interest of individuals and organizations in understanding public digital reputations.
              You have the right to:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Access your personal data</li>
              <li>Rectification of inaccurate data</li>
              <li>Erasure (&ldquo;right to be forgotten&rdquo;)</li>
              <li>Restrict processing</li>
              <li>Data portability</li>
              <li>Object to processing &mdash; if you object, we will cease processing unless we demonstrate compelling legitimate grounds</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Juvenile Content Policy</h2>
            <p className="text-slate-400 leading-relaxed">
              Content posted before the age of 18 is automatically excluded from score calculations when a
              date of birth is available. We believe people should not be judged for content posted as minors.
              If you believe juvenile content has been incorrectly included in a score, please contact us or
              file a dispute.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Abuse Prevention</h2>
            <p className="text-slate-400 leading-relaxed">
              To prevent misuse of our platform (bulk surveillance, harassment, automated scraping), we enforce:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">Rate limiting</strong> &mdash; all endpoints are rate-limited per IP address. Scan endpoints have stricter limits (10 per hour).</li>
              <li><strong className="text-slate-300">Daily scan caps</strong> &mdash; unauthenticated users may scan a maximum of 20 unique individuals per day per IP address.</li>
              <li><strong className="text-slate-300">Batch request limits</strong> &mdash; batch lookup requests are capped at 10 names per request for unauthenticated users.</li>
              <li><strong className="text-slate-300">Prohibited uses</strong> &mdash; our <Link to="/terms" className="text-indigo-400 hover:underline">Terms of Service</Link> prohibit using Cloak Haven for harassment, stalking, automated scraping, or any FCRA-regulated purpose.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">10. Data Security</h2>
            <p className="text-slate-400 leading-relaxed">
              We implement security measures including:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Passwords hashed with bcrypt (never stored in plaintext)</li>
              <li>JWT-based authentication with short-lived access tokens</li>
              <li>HTTPS encryption for all data in transit</li>
              <li>Rate limiting and abuse detection at the application layer</li>
              <li>Persistent rate limit storage that survives application restarts</li>
              <li>Payment processing handled entirely by Stripe (PCI-DSS compliant)</li>
              <li>Error monitoring via Sentry (no personal data in error reports)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">11. Third-Party Services</h2>
            <p className="text-slate-400 leading-relaxed">
              We use the following third-party services, each with their own privacy policies:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li><strong className="text-slate-300">SerpAPI</strong> &mdash; web search results (serpapi.com/privacy)</li>
              <li><strong className="text-slate-300">Twitter/X API</strong> &mdash; social media data (twitter.com/en/privacy)</li>
              <li><strong className="text-slate-300">YouTube Data API</strong> &mdash; video content (policies.google.com/privacy)</li>
              <li><strong className="text-slate-300">PeopleDataLabs</strong> &mdash; identity enrichment (peopledatalabs.com/privacy)</li>
              <li><strong className="text-slate-300">Anthropic (Claude)</strong> &mdash; AI-powered content classification (anthropic.com/privacy)</li>
              <li><strong className="text-slate-300">Stripe</strong> &mdash; payment processing (stripe.com/privacy)</li>
              <li><strong className="text-slate-300">SendGrid</strong> &mdash; transactional email (sendgrid.com/policies/privacy)</li>
              <li><strong className="text-slate-300">Sentry</strong> &mdash; error monitoring (sentry.io/privacy)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">12. Changes to This Policy</h2>
            <p className="text-slate-400 leading-relaxed">
              We may update this Privacy Policy from time to time. The &ldquo;Last updated&rdquo; date at the top of this
              page indicates when the policy was last revised. Material changes will be communicated via email
              to registered users. Continued use of the service after changes constitutes acceptance.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">13. Contact Us</h2>
            <p className="text-slate-400 leading-relaxed">
              For privacy-related inquiries, data requests, profile removal requests, or concerns:
            </p>
            <ul className="list-none text-slate-400 space-y-1 mt-2">
              <li>Privacy inquiries: <a href="mailto:privacy@cloakhaven.com" className="text-indigo-400 hover:underline">privacy@cloakhaven.com</a></li>
              <li>Profile removal: <a href="mailto:privacy@cloakhaven.com" className="text-indigo-400 hover:underline">privacy@cloakhaven.com</a> (subject: &ldquo;Profile Removal Request&rdquo;)</li>
              <li>General support: <a href="mailto:support@cloakhaven.com" className="text-indigo-400 hover:underline">support@cloakhaven.com</a></li>
            </ul>
            <p className="text-slate-400 leading-relaxed mt-3">
              We aim to respond to all privacy-related requests within 30 business days.
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
