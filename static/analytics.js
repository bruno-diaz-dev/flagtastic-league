// First-party page views on the public production domain only.
(() => {
    if (!["flagtastic.online", "www.flagtastic.online"].includes(window.location.hostname)) return;
    if (document.querySelector('script[src="/_vercel/insights/script.js"]')) return;

    window.va = window.va || function () {
        (window.vaq = window.vaq || []).push(arguments);
    };
    window.va("beforeSend", event => {
        if (event.type !== "pageview") return null;
        const url = new URL(event.url, window.location.origin);
        url.search = "";
        url.hash = "";
        return {...event, url: url.href};
    });

    const script = document.createElement("script");
    script.src = "/_vercel/insights/script.js";
    script.defer = true;
    document.head.appendChild(script);
})();
