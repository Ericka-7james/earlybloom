const FILTER_GROUPS = {
  experienceLevel: [
    { label: "Entry-level", value: "entry-level" },
    { label: "Junior", value: "junior" },
    { label: "Mid-level", value: "mid-level" },
    { label: "Senior", value: "senior" },
  ],
  workplace: [
    { label: "Remote", value: "remote" },
    { label: "Onsite", value: "onsite" },
    { label: "Hybrid", value: "hybrid" },
  ],
  roleType: [
    { label: "Frontend", value: "frontend" },
    { label: "Backend", value: "backend" },
    { label: "Full Stack", value: "full-stack" },
    { label: "Software Engineering", value: "software-engineering" },
    { label: "Mobile", value: "mobile" },
    { label: "Data", value: "data" },
    { label: "Data Engineering", value: "data-engineering" },
    { label: "Data Analyst", value: "data-analyst" },
    { label: "Machine Learning", value: "machine-learning" },
    { label: "AI", value: "ai" },
    { label: "DevOps", value: "devops" },
    { label: "SRE", value: "sre" },
    { label: "Cloud", value: "cloud" },
    { label: "Infrastructure", value: "infrastructure" },
    { label: "Cybersecurity", value: "cybersecurity" },
    { label: "QA", value: "qa" },
    { label: "Test Automation", value: "test-automation" },
    { label: "Product", value: "product" },
    { label: "Product Design", value: "product-design" },
    { label: "UX", value: "ux" },
    { label: "Solutions Engineering", value: "solutions-engineering" },
    { label: "Technical Support", value: "technical-support" },
    { label: "IT", value: "it" },
    { label: "Business Analyst", value: "business-analyst" },
    { label: "Platform", value: "platform" },
    { label: "Developer Tools", value: "developer-tools" },
  ],
};

const DEFAULT_SELECTED_EXPERIENCE_LEVELS = ["entry-level", "junior"];

function normalizeValue(value) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

function arraysEqualAsSets(left, right) {
  if (left.length !== right.length) {
    return false;
  }

  const leftSet = new Set(left);
  return right.every((value) => leftSet.has(value));
}

function toggleSelectedValue(currentValues, value) {
  if (currentValues.includes(value)) {
    return currentValues.filter((item) => item !== value);
  }

  return [...currentValues, value];
}

function getJobExperienceLevel(job) {
  const directLevel = normalizeValue(
    job.experienceLevel || job.experience_level || job.level
  );

  if (
    directLevel === "entry-level" ||
    directLevel === "junior" ||
    directLevel === "mid-level" ||
    directLevel === "senior"
  ) {
    return directLevel;
  }

  if (directLevel === "mid") {
    return "mid-level";
  }

  const haystack = normalizeValue(
    `${job.title || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (
    haystack.includes("entry-level") ||
    haystack.includes("entry level") ||
    haystack.includes("new grad") ||
    haystack.includes("graduate") ||
    haystack.includes("early career")
  ) {
    return "entry-level";
  }

  if (haystack.includes("junior") || haystack.includes("jr ")) {
    return "junior";
  }

  if (
    haystack.includes("senior") ||
    haystack.includes("staff") ||
    haystack.includes("principal") ||
    haystack.includes("lead") ||
    haystack.includes("chief") ||
    haystack.includes("director")
  ) {
    return "senior";
  }

  if (
    haystack.includes("mid-level") ||
    haystack.includes("mid level") ||
    haystack.includes("intermediate") ||
    haystack.includes("level ii") ||
    haystack.includes("level 2")
  ) {
    return "mid-level";
  }

  return "unknown";
}

function getJobWorkplace(job) {
  const remoteType = normalizeValue(job.remoteType || job.remote_type);
  if (
    remoteType === "remote" ||
    remoteType === "onsite" ||
    remoteType === "hybrid"
  ) {
    return remoteType;
  }

  if (job.remote === true) {
    return "remote";
  }

  const haystack = normalizeValue(
    `${job.location || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (haystack.includes("hybrid")) {
    return "hybrid";
  }

  if (haystack.includes("remote") || haystack.includes("telework")) {
    return "remote";
  }

  if (haystack.includes("onsite") || haystack.includes("on-site")) {
    return "onsite";
  }

  return "unknown";
}

function inferRoleType(job) {
  const directRoleType = normalizeValue(job.roleType || job.role_type);
  if (directRoleType) {
    return directRoleType;
  }

  const haystack = normalizeValue(
    `${job.title || ""} ${job.summary || ""} ${job.description || ""}`
  );

  if (
    haystack.includes("frontend") ||
    haystack.includes("front-end") ||
    haystack.includes("react") ||
    haystack.includes("ui engineer")
  ) {
    return "frontend";
  }

  if (
    haystack.includes("backend") ||
    haystack.includes("back-end") ||
    haystack.includes("api") ||
    haystack.includes("server-side")
  ) {
    return "backend";
  }

  if (
    haystack.includes("full stack") ||
    haystack.includes("full-stack") ||
    haystack.includes("fullstack")
  ) {
    return "full-stack";
  }

  if (
    haystack.includes("software engineer") ||
    haystack.includes("software developer") ||
    haystack.includes("application developer") ||
    haystack.includes("programmer")
  ) {
    return "software-engineering";
  }

  if (
    haystack.includes("ios") ||
    haystack.includes("android") ||
    haystack.includes("mobile")
  ) {
    return "mobile";
  }

  if (
    haystack.includes("data engineer") ||
    haystack.includes("etl") ||
    haystack.includes("pipeline")
  ) {
    return "data-engineering";
  }

  if (
    haystack.includes("data analyst") ||
    haystack.includes("business intelligence") ||
    haystack.includes("reporting analyst")
  ) {
    return "data-analyst";
  }

  if (
    haystack.includes("data ") ||
    haystack.includes("analytics") ||
    haystack.includes("analyst")
  ) {
    return "data";
  }

  if (
    haystack.includes("machine learning") ||
    haystack.includes("ml engineer")
  ) {
    return "machine-learning";
  }

  if (
    haystack.includes("artificial intelligence") ||
    haystack.includes(" ai ")
  ) {
    return "ai";
  }

  if (
    haystack.includes("devops") ||
    haystack.includes("devsecops") ||
    haystack.includes("ci/cd")
  ) {
    return "devops";
  }

  if (
    haystack.includes("site reliability") ||
    haystack.includes(" sre ")
  ) {
    return "sre";
  }

  if (haystack.includes("cloud")) {
    return "cloud";
  }

  if (
    haystack.includes("infrastructure") ||
    haystack.includes("sysadmin") ||
    haystack.includes("systems administration")
  ) {
    return "infrastructure";
  }

  if (
    haystack.includes("cyber") ||
    haystack.includes("security") ||
    haystack.includes("infosec")
  ) {
    return "cybersecurity";
  }

  if (
    haystack.includes("qa") ||
    haystack.includes("quality assurance") ||
    haystack.includes("test automation") ||
    haystack.includes("sdet")
  ) {
    return haystack.includes("automation") ? "test-automation" : "qa";
  }

  if (haystack.includes("product manager")) {
    return "product";
  }

  if (
    haystack.includes("product design") ||
    haystack.includes("product designer")
  ) {
    return "product-design";
  }

  if (
    haystack.includes("ux") ||
    haystack.includes("user experience") ||
    haystack.includes("ui/ux")
  ) {
    return "ux";
  }

  if (
    haystack.includes("solutions engineer") ||
    haystack.includes("sales engineer") ||
    haystack.includes("implementation engineer")
  ) {
    return "solutions-engineering";
  }

  if (
    haystack.includes("technical support") ||
    haystack.includes("support engineer") ||
    haystack.includes("help desk")
  ) {
    return "technical-support";
  }

  if (
    haystack.includes("it specialist") ||
    haystack.includes("it support") ||
    haystack.includes("information technology")
  ) {
    return "it";
  }

  if (
    haystack.includes("business analyst") ||
    haystack.includes("systems analyst")
  ) {
    return "business-analyst";
  }

  if (haystack.includes("platform")) {
    return "platform";
  }

  if (
    haystack.includes("developer tools") ||
    haystack.includes("devtools")
  ) {
    return "developer-tools";
  }

  return "unknown";
}

function filterJobs(
  jobs,
  { selectedExperienceLevels, selectedWorkplaces, selectedRoleTypes }
) {
  return jobs.filter((job) => {
    const experienceLevel = getJobExperienceLevel(job);
    const workplace = getJobWorkplace(job);
    const roleType = inferRoleType(job);

    const matchesExperienceLevel =
      selectedExperienceLevels.length === 0 ||
      selectedExperienceLevels.includes(experienceLevel);

    const matchesWorkplace =
      selectedWorkplaces.length === 0 ||
      selectedWorkplaces.includes(workplace);

    const matchesRoleType =
      selectedRoleTypes.length === 0 || selectedRoleTypes.includes(roleType);

    return matchesExperienceLevel && matchesWorkplace && matchesRoleType;
  });
}

function getFilterSummary({
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
}) {
  const parts = [];

  if (selectedExperienceLevels.length > 0) {
    parts.push(`${selectedExperienceLevels.length} level`);
  }

  if (selectedWorkplaces.length > 0) {
    parts.push(`${selectedWorkplaces.length} workplace`);
  }

  if (selectedRoleTypes.length > 0) {
    parts.push(`${selectedRoleTypes.length} role type`);
  }

  if (parts.length === 0) {
    return "All roles";
  }

  return parts.join(" • ");
}

function getActiveFilterTags({
  selectedExperienceLevels,
  selectedWorkplaces,
  selectedRoleTypes,
}) {
  const tags = [];

  FILTER_GROUPS.experienceLevel.forEach((option) => {
    if (selectedExperienceLevels.includes(option.value)) {
      tags.push({
        group: "Experience",
        label: option.label,
        value: option.value,
        type: "experience",
      });
    }
  });

  FILTER_GROUPS.workplace.forEach((option) => {
    if (selectedWorkplaces.includes(option.value)) {
      tags.push({
        group: "Workplace",
        label: option.label,
        value: option.value,
        type: "workplace",
      });
    }
  });

  FILTER_GROUPS.roleType.forEach((option) => {
    if (selectedRoleTypes.includes(option.value)) {
      tags.push({
        group: "Role type",
        label: option.label,
        value: option.value,
        type: "role",
      });
    }
  });

  return tags;
}

export {
  FILTER_GROUPS,
  DEFAULT_SELECTED_EXPERIENCE_LEVELS,
  arraysEqualAsSets,
  toggleSelectedValue,
  filterJobs,
  getFilterSummary,
  getActiveFilterTags,
};