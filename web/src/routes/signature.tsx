/**
 * Operator's email signature card — quick-access surface so the
 * gold/dark `24/7 GLOBAL AI` block can be previewed in the SPA
 * without opening an email client. Routed at `/signature`.
 *
 * The card is rendered as a literal HTML table (inline styles)
 * so it round-trips into Gmail / Outlook / Apple Mail exactly as
 * it would in a sent message. Tailwind only wraps the page frame
 * and the copy-source helper.
 */

export function SignatureRoute() {
  const html = SIGNATURE_HTML.trim();
  return (
    <div className="flex flex-col gap-6 py-6" data-testid="signature-route">
      <header>
        <h1 className="text-2xl font-semibold tracking-tight">
          Email signature
        </h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Copy the raw HTML into your mail client's signature
          settings. Preview below shows the rendered card.
        </p>
      </header>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Preview
        </h2>
        <div className="rounded-xl border bg-[#0F1116] p-8 shadow-sm">
          <div
            data-testid="signature-card"
            dangerouslySetInnerHTML={{ __html: html }}
          />
        </div>
      </section>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-medium uppercase tracking-wide text-muted-foreground">
          Raw HTML
        </h2>
        <pre className="max-h-80 overflow-auto rounded-lg border bg-muted/30 p-4 text-xs leading-relaxed">
          <code>{html}</code>
        </pre>
      </section>
    </div>
  );
}

const SIGNATURE_HTML = `
<table cellpadding="0" cellspacing="0" style="font-family: Arial, sans-serif; color:#EAEAEA;">
  <tr>
    <td style="padding-right:18px; vertical-align:top;">
      <div style="width:4px; height:90px; background:#C8A35F; border-radius:4px;"></div>
    </td>

    <td>
      <div style="font-size:24px; font-weight:700; color:#FFFFFF; letter-spacing:1px;">
        24/7 GLOBAL AI
      </div>

      <div style="font-size:13px; color:#C8A35F; margin-top:2px; letter-spacing:0.5px;">
        ALWAYS ON. ALWAYS SMART. ALWAYS GLOBAL.
      </div>

      <div style="margin-top:14px; font-size:15px; color:#FFFFFF; font-weight:600;">
        Chris West
      </div>

      <div style="font-size:13px; color:#A0A7B4;">
        Founder &amp; AI Systems Architect
      </div>

      <div style="margin-top:12px; font-size:13px; line-height:20px;">
        <span style="color:#FFFFFF;">📧</span>
        <span style="color:#C8A35F;">chris@247globalai.com</span>
        <br>

        <span style="color:#FFFFFF;">🌐</span>
        <span style="color:#C8A35F;">www.247globalai.com</span>
        <br>

        <span style="color:#FFFFFF;">📱</span>
        <span style="color:#C8A35F;">(970) 689-2591</span>
      </div>
    </td>
  </tr>
</table>
`;
