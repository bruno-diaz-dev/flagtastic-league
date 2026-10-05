# Navigation performance

Measured on production before this change: listing 101 teams with md5(logo_data) touched 6,758 buffer blocks and took 580 ms in PostgreSQL. Logos totalled 54.5 MB; runtime logs showed the team API taking 2.7 seconds and concurrent logo requests taking 0.75–1.4 seconds. These are server samples, not a claim about every user's complete load time.

Migration c4e8f0321b65 stores logo_version as a generated hash, computed on writes instead of reads. Apply it before deploying code to managed databases. Table RLS and the restricted backend role are unchanged. The revised listing query measured 3 ms and 10 buffer blocks. Standings group by the team's primary key rather than large logo bytes. Existing scores, ranking rules and identifiers remain unchanged.

Directory, schedule and standings use versioned 256-pixel WebP logo derivatives. Originals remain stored and available when size is omitted; invalid legacy rasters fall back to their original bytes. Responses retain CDN caching, and a new content version changes the image URL automatically.

Only the identical public HTML shells /teams, /games, /standings and /statistics are edge-cacheable for five minutes. Session checks and role-scoped APIs remain private and live game reads retain their existing refresh cadence. No browser history or authenticated user data is cached in these HTML responses.

Calendar OCR loads on demand from its existing pinned major-version CDN URL instead of blocking the games controller. Failed loads can be retried and simultaneous callers share one promise.

Verify with backend/JS tests, version replacement tests, public response cache headers and runtime timings. Client network latency and cold private requests may still vary; no infrastructure resizing or role/session caching is introduced.
