const estimateForm = document.querySelector("[data-estimate-url]");
if (estimateForm) {
  const category = estimateForm.elements.category;
  const condition = estimateForm.elements.device_condition;
  const conditionHelp = document.getElementById("condition-help");
  const output = estimateForm.querySelector("[data-estimate]");
  const note = estimateForm.querySelector("[data-estimate-note]");
  const format = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  });
  let activeRequest;

  async function updateEstimate() {
    activeRequest?.abort();
    conditionHelp.textContent = condition.selectedOptions[0].dataset.description
      || "Describe any defects in the listing.";
    if (!category.value || !condition.value) {
      output.textContent = "—";
      note.textContent = "Choose a category and condition to see an estimate.";
      return;
    }

    activeRequest = new AbortController();
    const params = new URLSearchParams({
      category: category.value,
      condition: condition.value,
    });
    output.textContent = "—";
    note.textContent = "Calculating estimate…";
    try {
      const response = await fetch(`${estimateForm.dataset.estimateUrl}?${params}`, {
        signal: activeRequest.signal,
      });
      if (!response.ok) throw new Error("Estimate unavailable");
      const result = await response.json();
      output.textContent = format.format(result.estimate);
      note.textContent = "Buyback requests use this amount.";
    } catch (error) {
      if (error.name === "AbortError") return;
      note.textContent = "The estimate will appear when you save the listing.";
    }
  }

  category.addEventListener("change", updateEstimate);
  condition.addEventListener("change", updateEstimate);
  updateEstimate();
}

const requestKind = document.querySelector("[data-request-kind]");
if (requestKind) {
  const details = document.querySelector("[data-exchange-details]");
  const field = details.querySelector("textarea");

  function updateRequestFields() {
    const isExchange = requestKind.value === "exchange";
    details.hidden = !isExchange;
    field.required = isExchange;
  }

  requestKind.addEventListener("change", updateRequestFields);
  updateRequestFields();
}
