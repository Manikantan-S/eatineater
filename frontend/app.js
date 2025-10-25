const API_BASE = "";

const form = document.getElementById("search-form");
const ingredientInput = document.getElementById("ingredient");
const cuisineSelect = document.getElementById("cuisine");
const dietSelect = document.getElementById("diet");
const maxTimeInput = document.getElementById("max-time");
const resetButton = document.getElementById("reset-btn");
const resultsList = document.getElementById("results");
const loadingIndicator = document.getElementById("loading");
const errorBox = document.getElementById("error");
const detailTitle = document.getElementById("detail-title");
const detailBody = document.getElementById("detail-body");
const detailTime = document.getElementById("detail-time");
const detailRating = document.getElementById("detail-rating");
const detailCuisines = document.getElementById("detail-cuisines");
const detailDiets = document.getElementById("detail-diets");
const detailUrl = document.getElementById("detail-url");
const detailIngredients = document.getElementById("detail-ingredients");
const detailDirections = document.getElementById("detail-directions");

async function fetchJson(path) {
  try {
    console.log(`Fetching: ${API_BASE}${path}`);
    const response = await fetch(`${API_BASE}${path}`);
    console.log(`Response status: ${response.status}`);
    
    if (!response.ok) {
      const message = await response.text();
      console.error(`Request failed: ${message}`);
      throw new Error(message || `Request failed with status ${response.status}`);
    }
    
    const data = await response.json();
    console.log(`Response data:`, data);
    return data;
  } catch (error) {
    console.error(`Fetch error for ${path}:`, error);
    throw error;
  }
}

function clearSelect(select) {
  while (select.options.length > 1) {
    select.remove(1);
  }
}

async function populateFilters() {
  try {
    const [diets, cuisines] = await Promise.all([
      fetchJson("/api/diets"),
      fetchJson("/api/cuisines"),
    ]);
    clearSelect(dietSelect);
    diets.forEach((diet) => {
      const option = document.createElement("option");
      option.value = diet;
      option.textContent = diet;
      dietSelect.append(option);
    });

    clearSelect(cuisineSelect);
    cuisines.forEach((cuisine) => {
      const option = document.createElement("option");
      option.value = cuisine;
      option.textContent = cuisine;
      cuisineSelect.append(option);
    });
  } catch (error) {
    console.error("Failed to populate filters", error);
    showError("Unable to load cuisines and diets. Try refreshing the page.");
  }
}

function showLoading(isLoading) {
  loadingIndicator.classList.toggle("hidden", !isLoading);
}

function showError(message) {
  if (!message) {
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
    return;
  }
  errorBox.textContent = message;
  errorBox.classList.remove("hidden");
}

function resetDetails() {
  detailTitle.textContent = "Select a recipe to see the details";
  detailBody.classList.add("hidden");
  detailIngredients.innerHTML = "";
  detailDirections.innerHTML = "";
}

function renderSummary(summary) {
  const item = document.createElement("li");
  item.className = "result-item";
  item.dataset.uri = summary.uri;

  const title = document.createElement("h3");
  title.textContent = summary.label;
  item.append(title);

  const meta = document.createElement("div");
  meta.className = "result-meta";
  if (summary.total_time !== null && summary.total_time !== undefined) {
    const timeSpan = document.createElement("span");
    timeSpan.textContent = `${summary.total_time} min`;
    meta.append(timeSpan);
  }
  if (summary.rating !== null && summary.rating !== undefined) {
    const ratingSpan = document.createElement("span");
    ratingSpan.textContent = `★ ${summary.rating.toFixed(1)}`;
    meta.append(ratingSpan);
  }
  if (summary.cuisines?.length) {
    summary.cuisines.forEach((cuisine) => {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = cuisine;
      meta.append(badge);
    });
  }
  if (summary.diets?.length) {
    summary.diets.forEach((diet) => {
      const badge = document.createElement("span");
      badge.className = "badge";
      badge.textContent = diet;
      meta.append(badge);
    });
  }

  item.append(meta);
  item.addEventListener("click", () => {
    document
      .querySelectorAll(".result-item")
      .forEach((node) => node.classList.remove("active"));
    item.classList.add("active");
    loadDetails(summary.uri);
  });
  return item;
}

function renderResults(results) {
  resultsList.innerHTML = "";
  if (!results.length) {
    const empty = document.createElement("li");
    empty.textContent = "No recipes match your filters yet.";
    resultsList.append(empty);
    resetDetails();
    return;
  }
  results.forEach((summary) => {
    const item = renderSummary(summary);
    resultsList.append(item);
  });
  // Auto-load the first recipe for convenience.
  loadDetails(results[0].uri);
  resultsList.firstElementChild.classList.add("active");
}

async function loadDetails(uri) {
  try {
    showError("");
    const detail = await fetchJson(`/api/recipes?uri=${encodeURIComponent(uri)}`);
    detailTitle.textContent = detail.label;
    detailBody.classList.remove("hidden");
    detailTime.textContent = detail.total_time ? `${detail.total_time} min` : "—";
    detailRating.textContent = detail.rating ? detail.rating.toFixed(1) : "—";
    detailCuisines.textContent = detail.cuisines?.join(", ") || "—";
    detailDiets.textContent = detail.diets?.join(", ") || "—";
    if (detail.url) {
      detailUrl.href = detail.url;
      detailUrl.textContent = "View recipe";
    } else {
      detailUrl.removeAttribute("href");
      detailUrl.textContent = "Not provided";
    }

    detailIngredients.innerHTML = "";
    detail.ingredients.forEach((ingredient) => {
      const li = document.createElement("li");
      li.textContent = ingredient;
      detailIngredients.append(li);
    });

    detailDirections.innerHTML = "";
    detail.directions.forEach((step) => {
      const li = document.createElement("li");
      li.textContent = step;
      detailDirections.append(li);
    });
  } catch (error) {
    console.error("Failed to load recipe details", error);
    showError("Unable to load the recipe details right now.");
  }
}

async function performSearch(event) {
  event?.preventDefault();
  const params = new URLSearchParams();
  if (ingredientInput.value.trim()) {
    params.set("ingredient", ingredientInput.value.trim());
  }
  if (cuisineSelect.value) {
    params.set("cuisine", cuisineSelect.value);
  }
  if (dietSelect.value) {
    params.set("diet", dietSelect.value);
  }
  if (maxTimeInput.value) {
    params.set("maxTime", maxTimeInput.value);
  }

  try {
    showLoading(true);
    showError("");
    console.log("Performing search with params:", params.toString());
    const data = await fetchJson(`/api/search?${params.toString()}`);
    console.log("Search results:", data);
    renderResults(data);
  } catch (error) {
    console.error("Search failed", error);
    showError(`Search failed: ${error.message}. Please check the console for details.`);
    resultsList.innerHTML = "";
  } finally {
    showLoading(false);
  }
}

function resetForm() {
  form.reset();
  performSearch();
}

form.addEventListener("submit", performSearch);
resetButton.addEventListener("click", resetForm);

document.addEventListener("DOMContentLoaded", async () => {
  await populateFilters();
  performSearch();
});
