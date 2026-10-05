# Production visitor analytics

Every page inheriting `templates/base.html` loads the small `static/analytics.js` initializer. It queues Vercel's documented beforeSend hook, then loads the first-party `/_vercel/insights/script.js` endpoint. That endpoint was confirmed to return JavaScript on flagtastic.online before integration. No npm build, React dependency or analytics API function is required for the Jinja application.

Only flagtastic.online and www.flagtastic.online initialize measurement. Preview URLs and localhost are excluded. Only page views are accepted; account attribution and custom events are not configured. Page URL query parameters and fragments are stripped before sending. Form contents are not captured. A load guard avoids duplicate scripts. Vercel controls visitor aggregation; page views are not the same as backend/API request counts.

Open https://vercel.com/bruno-diazs-projects-63b1093a/flagtastic-league/analytics and choose a date range to see Visitors, Page Views, top pages, sources and devices. If the dashboard has not been enabled, select Enable and redeploy. Historical visits made before instrumentation cannot be reconstructed from this integration.

References:
- https://vercel.com/docs/analytics/quickstart
- https://vercel.com/docs/analytics/package#beforesend

Verify the script's availability on production and inspect a normal browser's Network panel for POST /_vercel/insights/view after visiting a page. Headless browsers and tracking blockers can suppress measurement. Local unit tests verify host exclusion, single initialization and URL redaction without sending synthetic production visits.
