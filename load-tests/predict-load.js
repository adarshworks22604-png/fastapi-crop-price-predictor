import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "30s", target: 10 },
    { duration: "1m", target: 30 },
    { duration: "1m", target: 60 },
    { duration: "30s", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<1000"],
  },
};

const BASE = "http://127.0.0.1:8000";
const params = { headers: { "Content-Type": "application/json" } };

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  // Replace the body with your real PredictionRequest fields
  const body = JSON.stringify({ crop: "wheat" });
  const res = http.post(`${BASE}/predict/price`, body, params);
  check(res, {
    "predict 200": (r) => r.status === 200,
    "has a price": (r) => r.body.length > 0,
  });

  sleep(1);
}
