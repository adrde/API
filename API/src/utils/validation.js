export function parseNearbyQuery(query) {
  const errors = [];

  const lat = parseFloat(query.lat);
  const lon = parseFloat(query.lon);

  if (Number.isNaN(lat) || lat < -90 || lat > 90) {
    errors.push("Invalid 'lat' (must be -90 to 90).");
  }
  if (Number.isNaN(lon) || lon < -180 || lon > 180) {
    errors.push("Invalid 'lon' (must be -180 to 180).");
  }

  let radiusKm = query.radius_km !== undefined ? parseFloat(query.radius_km) : 20;
  if (Number.isNaN(radiusKm) || radiusKm <= 0) {
    errors.push("Invalid 'radius_km' (must be a positive number).");
  }

  let facilityType = (query.facility_type || "both").toLowerCase();
  if (!["helipad", "airstrip", "both"].includes(facilityType)) {
    errors.push("Invalid 'facility_type' (helipad | airstrip | both).");
  }

  return {
    lat,
    lon,
    radiusKm,
    facilityType,
    errors
  };
}
