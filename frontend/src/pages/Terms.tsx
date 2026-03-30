import { Link } from "react-router-dom";
import { FileText } from "lucide-react";
import Navbar from "@/components/Navbar";
import Footer from "@/components/Footer";
import { useDocumentTitle } from "@/hooks/useDocumentTitle";

export default function Terms() {
  useDocumentTitle("Terms of Service");
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
          <FileText className="w-8 h-8 text-indigo-400" />
          <h1 className="text-3xl font-bold text-white">Terms of Service</h1>
        </div>
        <p className="text-sm text-slate-500 mb-8">Last updated: March 25, 2026</p>

        <div className="prose prose-invert prose-sm max-w-none space-y-8">
          <section>
            <h2 className="text-xl font-semibold text-white mb-3">1. Acceptance of Terms</h2>
            <p className="text-slate-400 leading-relaxed">
              By accessing or using Cloak Haven ("the Service"), you agree to be bound by these Terms of Service.
              If you do not agree to these terms, do not use the Service. We reserve the right to update these
              terms at any time, and your continued use constitutes acceptance of any changes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">2. Service Description</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven provides online reputation scoring services. We analyze publicly available information
              and user-provided data to generate reputation scores and findings. Our scores are informational
              tools designed to help individuals understand and manage their digital presence.
            </p>
          </section>

          <section className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-6">
            <h2 className="text-xl font-semibold text-amber-400 mb-3">3. FCRA Disclaimer</h2>
            <p className="text-slate-300 leading-relaxed font-medium">
              IMPORTANT: Cloak Haven scores are NOT consumer reports as defined under the Fair Credit Reporting
              Act (FCRA), 15 U.S.C. 1681 et seq. Cloak Haven is NOT a consumer reporting agency.
            </p>
            <p className="text-slate-400 leading-relaxed mt-3">
              Cloak Haven scores and reports are not intended to be used, and shall not be used, as the sole
              basis for any decision regarding:
            </p>
            <ul className="list-disc list-inside text-slate-400 space-y-1 mt-2">
              <li>Employment or hiring decisions</li>
              <li>Tenant screening or housing decisions</li>
              <li>Credit or lending decisions</li>
              <li>Insurance underwriting</li>
              <li>Any other purpose governed by the FCRA</li>
            </ul>
            <p className="text-slate-400 leading-relaxed mt-3">
              Employers and other entities using Cloak Haven's employer tier acknowledge that Cloak Haven
              scores are supplementary information tools only and must not be the sole determinant in any
              decision affecting an individual. Users of the employer tier agree to comply with all applicable
              federal, state, and local laws regarding background checks and employment decisions.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">4. User Accounts</h2>
            <p className="text-slate-400 leading-relaxed">
              You are responsible for maintaining the confidentiality of your account credentials. You agree
              to provide accurate information during registration and to update your information as needed.
              You must be at least 18 years old to create an account.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">5. Scoring Methodology</h2>
            <p className="text-slate-400 leading-relaxed">
              Our scoring algorithm is transparent. Scores range from 0-1000 and are calculated based on
              three weighted components: Social Media History (40%), Web Presence (35%), and Posting
              Behavior (25%). Each finding is modified by recency, virality, and pattern factors.
              Content posted before age 18 (juvenile content) is automatically excluded from scoring.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">6. Dispute Process</h2>
            <p className="text-slate-400 leading-relaxed">
              Users may dispute any finding that they believe is inaccurate, outdated, or misclassified.
              Disputes are reviewed within 30 days. If a dispute is upheld (overturned), the finding
              is excluded from score calculations. Users have the right to provide supporting evidence
              with their dispute submission.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">7. Public Profiles</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven may create public profiles based on publicly available information. These profiles
              are created in the interest of transparency — showing individuals what information exists about
              them publicly. Any individual may claim their profile by verifying their identity. Unclaimed
              profiles display only information derived from publicly accessible sources.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">8. Data Upload & Zero Retention</h2>
            <p className="text-slate-400 leading-relaxed">
              When you upload data archives from social media platforms, the raw files are processed to
              extract findings and are then permanently deleted. We do not retain, store, or back up
              your original data exports. Only the classified findings (category, severity, and score impact)
              are retained as part of your profile.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">9. Payments & Refunds</h2>
            <p className="text-slate-400 leading-relaxed">
              Payments are processed securely through Stripe. Subscription plans may be cancelled at any
              time. One-time audit payments are non-refundable once the audit has been initiated. Monthly
              subscriptions may be cancelled before the next billing cycle for a prorated refund.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">10. Limitation of Liability</h2>
            <p className="text-slate-400 leading-relaxed">
              Cloak Haven provides scores and findings on an "as is" basis. We make no warranties,
              express or implied, regarding the accuracy, completeness, or fitness for a particular
              purpose of our scores. In no event shall Cloak Haven be liable for any indirect,
              incidental, special, or consequential damages arising from your use of the Service.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">11. Prohibited Uses</h2>
            <ul className="list-disc list-inside text-slate-400 space-y-1">
              <li>Using scores as the sole basis for employment, housing, credit, or insurance decisions</li>
              <li>Harassment, stalking, or intimidation of scored individuals</li>
              <li>Automated scraping or bulk data collection from the platform</li>
              <li>Creating false accounts or submitting fraudulent disputes</li>
              <li>Attempting to manipulate or game the scoring algorithm</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-3">12. Contact</h2>
            <p className="text-slate-400 leading-relaxed">
              For questions about these terms:<br />
              Email: <a href="mailto:support@cloakhaven.com" className="text-indigo-400 hover:underline">support@cloakhaven.com</a><br />
              Legal inquiries: <a href="mailto:privacy@cloakhaven.com" className="text-indigo-400 hover:underline">privacy@cloakhaven.com</a>
            </p>
          </section>
        </div>
      </main>

      <Footer />
    </div>
  );
}
