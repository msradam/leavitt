// k6 load generator for the OpenTelemetry Demo, replacing the Locust loadgen.
// Mirrors the Locust shopping journey (same endpoints and task weights) so the
// flagd chaos scenarios still trigger. Requests are tagged by endpoint name so
// k6's client-side metrics (k6_http_req_failed, k6_http_req_duration) break down
// per endpoint in Prometheus, which Leavitt reads as a client-side symptom source.
//
// Metrics are remote-written to Prometheus (K6_PROMETHEUS_RW_SERVER_URL). Run via
// the k6 service in compose.leavitt-k6.yaml.

import http from "k6/http";
import { sleep } from "k6";

const BASE = __ENV.TARGET || "http://frontend-proxy:8080";

const PRODUCTS = [
  "0PUK6V6EV0", "1YMWWN1N4O", "2ZYFJ3GM2N", "66VCHSJNUP", "6E92ZMYYFZ",
  "9SIQT8TOJO", "L9ECAV7KIM", "LS4PSXUNUM", "OLJCESPC7Z", "HQTGWGPNH4",
];
const CATEGORIES = ["binoculars", "telescopes", "accessories", "assembly", "travel", "books", ""];
const PERSON = {
  email: "larry_sergei@example.com",
  address: { streetAddress: "1600 Amphitheatre Parkway", zipCode: "94043", city: "Mountain View", state: "CA", country: "United States" },
  userCurrency: "USD",
  creditCard: { creditCardNumber: "4432-8015-6152-0454", creditCardExpirationMonth: 1, creditCardExpirationYear: 2039, creditCardCvv: 672 },
};

export const options = {
  scenarios: {
    shoppers: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 24),
      duration: __ENV.DURATION || "720h",
    },
  },
  // Surface client-side errors as metrics; do not abort the run on them.
  thresholds: {},
};

const rand = (arr) => arr[Math.floor(Math.random() * arr.length)];
const rid = () => `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
const JSON_HDR = { headers: { "Content-Type": "application/json" } };

// Task weights mirror the Locust @task(n) values.
const TASKS = [
  ["index", 1], ["browse_product", 10], ["recommendations", 3], ["reviews", 2],
  ["ask_ai", 1], ["ads", 3], ["view_cart", 3], ["add_to_cart", 2], ["checkout", 1],
];
const WEIGHTED = TASKS.flatMap(([name, w]) => Array(w).fill(name));

function addToCart(userId) {
  const product = rand(PRODUCTS);
  http.get(`${BASE}/api/products/${product}`, { tags: { name: "product" } });
  const body = JSON.stringify({ item: { productId: product, quantity: rand([1, 2, 3, 4, 5]) }, userId });
  http.post(`${BASE}/api/cart`, body, { ...JSON_HDR, tags: { name: "cart_add" } });
}

export default function () {
  const task = rand(WEIGHTED);
  if (task === "index") {
    http.get(`${BASE}/`, { tags: { name: "index" } });
  } else if (task === "browse_product") {
    http.get(`${BASE}/api/products/${rand(PRODUCTS)}`, { tags: { name: "product" } });
  } else if (task === "recommendations") {
    http.get(`${BASE}/api/recommendations?productIds=${rand(PRODUCTS)}`, { tags: { name: "recommendations" } });
  } else if (task === "reviews") {
    http.get(`${BASE}/api/product-reviews/${rand(PRODUCTS)}`, { tags: { name: "reviews" } });
  } else if (task === "ask_ai") {
    http.post(`${BASE}/api/product-ask-ai-assistant/${rand(PRODUCTS)}`,
      JSON.stringify({ question: "Can you summarize the product reviews?" }),
      { ...JSON_HDR, tags: { name: "ask_ai" } });
  } else if (task === "ads") {
    http.get(`${BASE}/api/data/?contextKeys=${rand(CATEGORIES)}`, { tags: { name: "ads" } });
  } else if (task === "view_cart") {
    http.get(`${BASE}/api/cart`, { tags: { name: "cart_view" } });
  } else if (task === "add_to_cart") {
    addToCart(rid());
  } else if (task === "checkout") {
    const userId = rid();
    addToCart(userId);
    http.post(`${BASE}/api/checkout`, JSON.stringify({ ...PERSON, userId }), { ...JSON_HDR, tags: { name: "checkout" } });
  }
  // Modulate think time on a slow shared wave so aggregate throughput rises and
  // falls (constant VUs alone produce a flat rate). Keeps the run continuous.
  const phase = Math.sin(Date.now() / 8000);
  sleep(2.25 + 1.75 * phase + Math.random() * 0.5);
}
