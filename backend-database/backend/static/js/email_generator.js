document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("email-gen-form");
  const resultArea = document.getElementById("result-area");
  let lastPayload = null;

  form.addEventListener("submit", async e => {
    e.preventDefault();
    resultArea.innerHTML = "<em>Generating…</em>";

    // collect context points
    const contextPoints = [
      form.context_point_1.value.trim(),
      form.context_point_2.value.trim(),
      form.context_point_3.value.trim()
    ];
    const optional = form.optional_context.value.trim();
    if (optional) contextPoints.push(optional);

    // build base payload (no tones field here)
    const payload = {
      company_name:       form.company_name.value.trim(),
      industry:           form.industry.value.trim(),
      focus:              form.focus.value,
      additional_context: contextPoints,
      model_choice:       form.model_choice.value,
      user_id:            "anonymous"
    };
    lastPayload = { ...payload };

    try {
      const res = await fetch("/api/generate-email-all-tones", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || res.statusText);
      }
      const results = await res.json();

      // render each tone block
      let html = `<h2>Generated Emails</h2>`;
      results.forEach(r => {
        html += `
          <div class="email-block"
               data-message-id="${r.message_id}"
               data-tone="${r.tone}">
            <h3>Tone: ${r.tone}</h3>
            <div class="message-text">
              <pre>${r.message}</pre>
            </div>
            <div class="controls">
              <button class="btn upvote">👍 Upvote</button>
              <button class="btn downvote">👎 Downvote</button>
              <button class="btn regenerate">🔁 Regenerate</button>
            </div>
          </div>
          <hr/>`;
      });
      resultArea.innerHTML = html;

      // wire up feedback + regeneration
      document.querySelectorAll(".email-block").forEach(block => {
        const messageId = block.dataset.messageId;
        const tone      = block.dataset.tone;
        const text      = block.querySelector("pre").innerText;

        block.querySelector(".upvote").onclick = () => sendFeedback({
          message_id: messageId,
          feedback_type: "upvote",
          tone, text
        });
        block.querySelector(".downvote").onclick = () => sendFeedback({
          message_id: messageId,
          feedback_type: "downvote",
          tone, text
        });
        block.querySelector(".regenerate").onclick = async () => {
          block.querySelector(".regenerate").disabled = true;
          await regenerateTone(messageId, tone, block);
          block.querySelector(".regenerate").disabled = false;
        };
      });
    } catch (err) {
      resultArea.innerHTML = `<p style="color:red;">Error: ${err.message}</p>`;
    }
  });


  async function sendFeedback({ message_id, feedback_type, tone, text }) {
    const payload = {
      message_id,
      feedback_type,
      user_id:         lastPayload.user_id,
      company_name:    lastPayload.company_name,
      industry:        lastPayload.industry,
      tone,
      focus:           lastPayload.focus,
      context:         lastPayload.additional_context.join(" "),
      model_used:      lastPayload.model_choice,
      prompt_template: `${tone}_${lastPayload.focus}_1`,
      prompt_text:     "",
      generated_message: { message: text, generated_at: new Date().toISOString() }
    };
    const res = await fetch("/api/feedback", {
      method:  "POST",
      headers: { "Content-Type":"application/json" },
      body:    JSON.stringify(payload)
    });
    const result = await res.json();
    alert(res.ok ? `✅ ${feedback_type} recorded` : `❌ feedback failed: ${result.error}`);
  }

  async function regenerateTone(parent_message_id, tone, block) {
    const regenPayload = {
      ...lastPayload,
      parent_message_id,
      tones: [tone]
    };
    const res = await fetch("/api/generate-email-all-tones", {
      method:  "POST",
      headers: { "Content-Type":"application/json" },
      body:    JSON.stringify(regenPayload)
    });
    if (!res.ok) {
      const err = await res.json();
      return alert("Regen failed: " + err.error);
    }
    const [r] = await res.json();
    block.querySelector("pre").innerText    = r.message;
    block.dataset.messageId               = r.message_id;

    // auto‐record the regeneration
    sendFeedback({
      message_id: r.message_id,
      feedback_type: "regeneration",
      tone,
      text: r.message
    });
  }
});
