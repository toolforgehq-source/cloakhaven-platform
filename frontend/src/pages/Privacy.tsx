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
        <p className="text-sm text-slate-500 mb-8">Last updated: March 25, 2026</p>

        <div className="prose prose-invert prose-sm max-w-none space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Introduction</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven ("we," "our," or "us") operates the cloakhaven.com website and related services.
              This Privacy Policy explains how we collect, use, disclose, and safeguard your information when
              you use our platform. We are committed to protecting your privacy and ensuring transparency in
              all our data practices.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. Information We Collect</h2>
            <h3 className="text-lg font-medium text-slate-300 mb-2">2.1 Information You Provide</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Account registration data (name, email, password)</li>
              <li>Social media account connections (via OAuth)</li>
              <li>Data archive uploads (processed and immediately deleted — zero retention)</li>
              <li>Dispute submissions and supporting evidence</li>
              <li>Payment information (processed securely by Stripe)</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">2.2 Information We Collect Automatically</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Public social media data accessible via platform APIs</li>
              <li>Public web presence data via search engine results</li>
              <li>Usage data (pages visited, features used)</li>
              <li>Device and browser information</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">3. Zero Data Retention Policy</h2>
            <p className="text-slate-400 leading-relaxed">
              When you upload data archives (Instagram, TikTok, Facebook, LinkedIn exports), we process the
              content to generate findings and scores, then <strong className="text-white">immediately and permanently
              delete the raw uploaded files</strong>. We do not store, copy, or retain your original data exports.
              Only the classified findings (category, severity, score impact) are retained — never the raw content.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. How We Use Your Information</h2>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>To calculate and maintain your reputation score</li>
              <li>To provide detailed findings and risk assessments</li>
              <li>To process disputes and update scores accordingly</li>
              <li>To send transactional emails (verification, score updates, dispute notifications)</li>
              <li>To process payments through Stripe</li>
              <li>To improve our scoring algorithms and services</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Juvenile Content Policy</h2>
            <p className="text-slate-400 leading-relaxed">
              Content posted before the age of 18 is automatically excluded from score calculations.
              If you provide your date of birth, our system identifies and flags juvenile content,
              ensuring it does not negatively impact your reputation score. We believe people should
              not be judged for content posted as minors.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. Public Profiles</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven may create public profiles based on publicly available information. These profiles
              display an unverified score based solely on public data. Any person can claim their profile
              by creating an account and verifying their identity. Claimed profiles can be enhanced with
              private data uploads for a more accurate, verified score.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Your Rights</h2>
            <h3 className="text-lg font-medium text-slate-300 mb-2">CCPA (California Residents)</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Right to know what personal information we collect</li>
              <li>Right to delete your personal information</li>
              <li>Right to opt-out of the sale of personal information (we do not sell data)</li>
              <li>Right to non-discrimination for exercising your rights</li>
            </ul>

            <h3 className="text-lg font-medium text-slate-300 mb-2 mt-4">GDPR (EU/EEA Residents)</h3>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Right of access to your personal data</li>
              <li>Right to rectification of inaccurate data</li>
              <li>Right to erasure ("right to be forgotten")</li>
              <li>Right to restrict processing</li>
              <li>Right to data portability</li>
              <li>Right to object to processing</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Data Security</h2>
            <p className="text-slate-400 leading-relaxed">
              We implement industry-standard security measures including encryption at rest and in transit,
              secure authentication with JWT tokens and bcrypt password hashing, rate limiting, and regular
              security audits. Payment processing is handled entirely by Stripe and we never store credit
              card information.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Contact Us</h2>
            <p className="text-slate-400 leading-relaxed">
              For privacy-related inquiries, data requests, or concerns:<br />
              Email: <a href="mailto:privacy@cloakhaven.com" className="text-indigo-400 hover:underline">privacy@cloakhaven.com</a>
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
