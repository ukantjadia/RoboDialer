"use client";
import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
// import { useEffect, useState } from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip as RechartTooltip,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  LineChart,
  Line,
  Legend,
  ResponsiveContainer,
} from "recharts";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import {
  Search,
  Download,
  ArrowLeft,
  Filter,
  X,
  ExternalLink,
  Forward,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "@/components/ui/select";
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationLink,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import axios from "axios";
import useEmailVerificationGuard from "@/hooks/useEmailVerificationGuard";
import Notif from "@/components/ui/notif";
import Popup from "@/components/ui/popup";
import FeedbackPopup from "@/components/FeedbackPopup";
import { SortDropdown } from "@/components/ui/sort-dropdown";
import Footer from "@/components/footer";
import { redirect } from "next/navigation";
import dayjs from "dayjs";
const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;
const DATABASE_URL_NOAPI = DATABASE_URL?.replace(/\/api\/?$/, "");

// export default function Home() {
//   redirect('/auth');
// }
export default function Home() {
  const { showPopup, handleClose } = useEmailVerificationGuard();
  const user =
    typeof window !== "undefined"
      ? JSON.parse(sessionStorage.getItem("user") || "{}")
      : {};
  const userTier = user?.tier || "free";
  const [searchTerm, setSearchTerm] = useState("");
  const [employeesFilter, setEmployeesFilter] = useState("");
  const [revenueFilter, setRevenueFilter] = useState("");
  const [businessTypeFilter, setBusinessTypeFilter] = useState("");
  const [productFilter, setProductFilter] = useState("");
  const [yearFoundedFilter, setYearFoundedFilter] = useState("");
  const [bbbRatingFilter, setBbbRatingFilter] = useState("");
  const [streetFilter, setStreetFilter] = useState("");
  const [industryFilter, setIndustryFilter] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [stateFilter, setStateFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [showFilters, setShowFilters] = useState(false);
  const [selectAll, setSelectAll] = useState(false);
  const [hasSorted, setHasSorted] = useState(false);
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showReactivateConfirm, setShowReactivateConfirm] = useState(false);

  // Forward functionality state
  const [showForwardDropdown, setShowForwardDropdown] = useState(false);
  const [teams, setTeams] = useState([]);
  const [projects, setProjects] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [selectedTeam, setSelectedTeam] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [selectedTask, setSelectedTask] = useState("");
  const [forwardStep, setForwardStep] = useState("team"); // "team", "project", "task"
  const [isLoadingForward, setIsLoadingForward] = useState(false);

  const router = useRouter();
  const handleSave = async (index) => {
    // Helper to convert camelCase keys into snake_case
    const toSnake = (str) => str.replace(/([A-Z])/g, "_$1").toLowerCase();

    // Given a plain object with camelCase keys, return a new object
    // whose keys are all snake_case.
    const normalizeKeys = (obj) => {
      const result = {};
      for (const [k, v] of Object.entries(obj)) {
        result[toSnake(k)] = v;
      }
      return result;
    };

    try {
      const lead = editedRows[index];
      const leadId = lead.lead_id || lead.id;
      const originalDraftId = lead.draft_id;

      // Normalize the edited fields so that every key is snake_case:
      const normalizedLead = normalizeKeys(lead);
      // Always include user_id in snake_case:
      normalizedLead.user_id = user.id;

      // 1) Always call POST first
      const postResponse = await axios.post(
        `${DATABASE_URL_NOAPI}/leads/${leadId}/edit`,
        normalizedLead,
        { withCredentials: true }
      );
      showNotification("Draft POST called successfully", "success");

      // If the POST returned a new draft_id, use it; otherwise keep originalDraftId
      const newDraftId = postResponse.data?.draft?.draft_id;
      const actualDraftId = newDraftId || originalDraftId;

      // 2) Now call PUT to update that draft
      const payload = {
        draft_data: normalizedLead,
        change_summary: "Updated from homepage",
        phase: "draft",
        status: "pending",
      };

      await axios.put(
        `${DATABASE_URL}/leads/drafts/${actualDraftId}`,
        payload,
        { withCredentials: true }
      );
      showNotification("Draft updated successfully", "success");

      // Reflect changes in local state (ensure draft_id is set)
      const updated = [...scrapingHistory];
      updated[index] = {
        ...lead,
        draft_id: actualDraftId,
        updated: new Date().toLocaleString(),
      };
      setScrapingHistory(updated);
      setEditedRows(updated);
      setEditingRowIndex(null);
    } catch (err) {
      console.error("❌ Error saving row:", err);
      showNotification("Failed to save row.", "error");
    }
  };

  const handleDiscard = (index) => {
    const resetRow = scrapingHistory[index];
    const updated = [...editedRows];
    updated[index] = resetRow;
    setEditedRows(updated);
    setEditingRowIndex(null);
  };

  const handleFieldChange = (index, field, value) => {
    const updated = [...editedRows];
    updated[index] = {
      ...updated[index],
      [field]: value,
    };
    setEditedRows(updated);
  };

  const [notif, setNotif] = useState({
    show: false,
    message: "",
    type: "success",
  });
  const showNotification = (message, type = "success") => {
    setNotif({ show: true, message, type });

    // Automatically hide after X seconds (let Notif handle it visually)
    // Optional if Notif itself auto-hides — but helpful as backup
    setTimeout(() => {
      setNotif((prev) => ({ ...prev, show: false }));
    }, 3500);
  };

  const [editingRowIndex, setEditingRowIndex] = useState(null);

  const clearAllFilters = () => {
    setEmployeesFilter("");
    setRevenueFilter("");
    setBusinessTypeFilter("");
    setProductFilter("");
    setYearFoundedFilter("");
    setBbbRatingFilter("");
    setStreetFilter("");
    setCityFilter("");
    setStateFilter("");
    setSourceFilter("");
  };

  const parseRevenue = (revenueInput) => {
    if (typeof revenueInput === "number") return revenueInput;
    if (typeof revenueInput !== "string") return null;

    let revenueStr = revenueInput.toLowerCase().trim().replace(/[$,]/g, "");
    let multiplier = 1;

    if (revenueStr.endsWith("k")) {
      multiplier = 1_000;
      revenueStr = revenueStr.slice(0, -1);
    } else if (revenueStr.endsWith("m")) {
      multiplier = 1_000_000;
      revenueStr = revenueStr.slice(0, -1);
    } else if (revenueStr.endsWith("b")) {
      multiplier = 1_000_000_000;
      revenueStr = revenueStr.slice(0, -1);
    }

    const value = parseFloat(revenueStr);
    return isNaN(value) ? null : value * multiplier;
  };

  const parseFilter = (filterStr, isRevenue = false) => {
    const result = {
      operation: "exact",
      value: null | null,
      upper: null | null,
    };
    filterStr = filterStr.toLowerCase().trim();
    const rangeMatch = filterStr.match(
      /^(\d+(?:[kmb]?)?)\s*-\s*(\d+(?:[kmb]?)?)$/
    );
    if (rangeMatch) {
      const val1 = isRevenue
        ? parseRevenue(rangeMatch[1])
        : parseInt(rangeMatch[1]);
      const val2 = isRevenue
        ? parseRevenue(rangeMatch[2])
        : parseInt(rangeMatch[2]);
      return { operation: "between", value: val1, upper: val2 };
    }
    if (filterStr.startsWith(">="))
      (result.operation = "greater than or equal"),
        (filterStr = filterStr.slice(2));
    else if (filterStr.startsWith(">"))
      (result.operation = "greater than"), (filterStr = filterStr.slice(1));
    else if (filterStr.startsWith("<="))
      (result.operation = "less than or equal"),
        (filterStr = filterStr.slice(2));
    else if (filterStr.startsWith("<"))
      (result.operation = "less than"), (filterStr = filterStr.slice(1));
    result.value = isRevenue ? parseRevenue(filterStr) : parseInt(filterStr);
    return result;
  };

  const toCamelCase = (str) =>
    str.replace(/([-_][a-z])/gi, (group) =>
      group.toUpperCase().replace("-", "").replace("_", "")
    );

  const toCamelCaseKeys = (obj) => {
    const newObj = {};
    for (const key in obj) {
      const camelKey = toCamelCase(key);
      newObj[camelKey] = obj[key];
    }
    return newObj;
  };

  //

  const ExpandableCell = ({ text }) => {
    const [expanded, setExpanded] = useState(false);
    
    // Ensure text is always a string and handle null/undefined cases
    const safeText = text != null ? String(text) : "";
    const isLong = safeText.length > 100;

    if (!isLong) return <span>{safeText}</span>;

    return (
      <div className="whitespace-pre-wrap">
        <span>{expanded ? safeText : safeText.slice(0, 30) + "... "}</span>
        <button
          className="text-blue-500 hover:underline text-xs ml-1"
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      </div>
    );
  };

  const handleExportCSVWithCredits = async () => {
    try {
      // Check if any items are selected
      if (selectedCompanies.length === 0) {
        showNotification(
          "Please select at least one company to export.",
          "info"
        );
        return;
      }

      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        {
          withCredentials: true,
        }
      );

      const planName =
        subscriptionInfo?.subscription?.plan_name?.toLowerCase() ?? "free";
      const availableCredits =
        subscriptionInfo?.subscription?.credits_remaining ?? 0;
      const requiredCredits = selectedCompanies.length;
      const userRole = user?.role || "user";

      // Allow export if user is developer OR has non-free tier
      const isDeveloper = userRole === "developer";
      const hasNonFreeTier = planName !== "free";

      if (!isDeveloper && !hasNonFreeTier) {
        showNotification(
          "Exporting requires either a paid subscription or developer role. Please upgrade your plan or contact support.",
          "info"
        );
        return;
      }

      // If developer, skip credit check
      if (isDeveloper) {
        // Get selected items from scrapingHistory
        const selectedItems = scrapingHistory.filter(item =>
          selectedCompanies.includes(item.id)
        );
        handleExportCSV(selectedItems, "scraping_history.csv");
        showNotification(`Successfully exported ${selectedItems.length} selected items.`, "success");
        return;
      }

      // For non-developers with paid tier, check credits
      if (availableCredits < requiredCredits) {
        showNotification(
          "Insufficient credits to export all selected leads. Please upgrade or reduce selection.",
          "error"
        );
        return;
      }

      // Get selected items from scrapingHistory
      const selectedItems = scrapingHistory.filter(item =>
        selectedCompanies.includes(item.id)
      );

      handleExportCSV(selectedItems, "scraping_history.csv");
      showNotification(`Successfully exported ${selectedItems.length} selected items.`, "success");
    } catch (checkErr) {
      console.error("❌ Failed to verify subscription:", checkErr);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
    }
  };

  const handleReactivateSubscription = async () => {
    try {
      const res = await axios.post(
        `${DATABASE_URL}/subscription/resume`,
        {},
        { withCredentials: true }
      );
      if (res.status === 200) {
        showNotification("Subscription reactivated!", "success");
        // Refresh page
        window.location.reload();
      } else {
        showNotification("Failed to reactivate subscription.", "error");
      }
    } catch (err) {
      showNotification("Error reactivating subscription.", "error");
    }
  };

  const handleToggleFiltersWithCheck = async () => {
    try {
      const { data: subscriptionInfo } = await axios.get(
        `${DATABASE_URL}/user/subscription_info`,
        { withCredentials: true }
      );
      const planName =
        subscriptionInfo?.subscription?.plan_name?.toLowerCase() ?? "free";
      if (planName === "free") {
        showNotification(
          "Advanced filters are disabled on the Free tier. Please upgrade your plan.",
          "info"
        );
        return;
      }
      setShowFilters((prev) => !prev);
    } catch (err) {
      console.error("❌ Failed to verify subscription:", err);
      showNotification(
        "Failed to verify your subscription. Please try again later.",
        "error"
      );
    }
  };

  // Forward functionality API functions
  const fetchTeams = async () => {
    try {
      setIsLoadingForward(true);
      const response = await axios.get(`${DATABASE_URL}/workspace/`, {
        withCredentials: true,
      });
      console.log("Teams API response:", response.data);
      console.log("Response data workspaces:", response.data.workspaces);
      console.log("Setting teams to:", response.data.workspaces || []);
      setTeams(response.data.workspaces || []);
    } catch (error) {
      console.error("Error fetching teams:", error);
      showNotification("Failed to fetch teams", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const fetchProjects = async (teamId) => {
    try {
      setIsLoadingForward(true);
      const response = await axios.get(`${DATABASE_URL}/workspace/${teamId}/projects`, {
        withCredentials: true,
      });
      setProjects(response.data.projects || []);
    } catch (error) {
      console.error("Error fetching projects:", error);
      showNotification("Failed to fetch projects", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const fetchTasks = async (teamId, projectId) => {
    try {
      setIsLoadingForward(true);
      const response = await axios.get(`${DATABASE_URL}/workspace/projects/${projectId}/tasks`, {
        withCredentials: true,
      });
      // Handle the nested structure like in AdminProjectView
      const data = response.data;
      const allTasks = [
        ...(data.tasks?.todo || []),
        ...(data.tasks?.in_progress || []),
        ...(data.tasks?.review || []),
        ...(data.tasks?.done || [])
      ];
      setTasks(allTasks);
    } catch (error) {
      console.error("Error fetching tasks:", error);
      showNotification("Failed to fetch tasks", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const handleForwardClick = () => {
    if (selectedCompanies.length === 0) {
      showNotification("Please select at least one lead to forward", "info");
      return;
    }
    setShowForwardDropdown(!showForwardDropdown);
    setForwardStep("team");
    setSelectedTeam("");
    setSelectedProject("");
    setSelectedTask("");
    if (!showForwardDropdown) {
      fetchTeams();
    }
  };

  const handleTeamSelect = (workspaceId) => {
    setSelectedTeam(workspaceId);
    setForwardStep("project");
    setSelectedProject("");
    setSelectedTask("");
    fetchProjects(workspaceId);
  };

  const handleProjectSelect = (projectId) => {
    setSelectedProject(projectId);
    setForwardStep("task");
    setSelectedTask("");
    fetchTasks(selectedTeam, projectId);
  };

  const handleTaskSelect = async (taskId) => {
    setSelectedTask(taskId);
    setIsLoadingForward(true);
    
    try {
      // Get the selected companies data
      const selectedItems = scrapingHistory.filter(item => selectedCompanies.includes(item.id));
      
      // Forward each selected company
      for (const company of selectedItems) {
        const payload = {
          task_id: taskId,
          draft_id: company.draft_id || company.id,
          title: `Lead Draft: ${company.company || 'Unknown Company'}`,
          description: `Company: ${company.company || 'Unknown'}, Contact: ${company.ownerFirstName || ''} ${company.ownerLastName || ''}, Email: ${company.ownerEmail || 'No email'}`,
          priority: "medium",
          status: "todo",
          due_date: null
        };

        await axios.post(
          `${DATABASE_URL}/workspace/${selectedTeam}/tasks/forward-user-lead-draft`,
          payload,
          { withCredentials: true }
        );
      }
      
      showNotification(`Successfully forwarded ${selectedCompanies.length} leads to selected task`, "success");
      setShowForwardDropdown(false);
      setForwardStep("team");
      setSelectedTeam("");
      setSelectedProject("");
      setSelectedTask("");
    } catch (error) {
      console.error("Error forwarding leads:", error);
      showNotification("Failed to forward leads to task", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const [scrapingHistory, setScrapingHistory] = useState([]);

  const handleExportCSV = (itemsToExport = currentItems, filename = "scraping_history.csv") => {
    const headers = [
      "Company",
      "Website",
      "Industry",
      "Product Category",
      "Business Type",
      "Employees",
      "Revenue",
      "Year Founded",
      "BBB Rating",
      "Street",
      "City",
      "State",
      "Company Phone",
      "Company LinkedIn",
      "Owner First Name",
      "Owner Last Name",
      "Owner Title",
      "Owner LinkedIn",
      "Owner Phone Number",
      "Owner Email",
      "Source",
      "Created At",
      "Updated At",
    ];

    // Create a mapping from header names to actual field names
    const headerToFieldMap = {
      "Company": "company",
      "Website": "website",
      "Industry": "industry",
      "Product Category": "productCategory",
      "Business Type": "businessType",
      "Employees": "employees",
      "Revenue": "revenue",
      "Year Founded": "yearFounded",
      "BBB Rating": "bbbRating",
      "Street": "street",
      "City": "city",
      "State": "state",
      "Company Phone": "companyPhone",
      "Company LinkedIn": "companyLinkedin",
      "Owner First Name": "ownerFirstName",
      "Owner Last Name": "ownerLastName",
      "Owner Title": "ownerTitle",
      "Owner LinkedIn": "ownerLinkedin",
      "Owner Phone Number": "ownerPhoneNumber",
      "Owner Email": "ownerEmail",
      "Source": "source",
      "Created At": "created",
      "Updated At": "updated",
    };

    const csvContent = [
      headers.join(","), // Header row
      ...itemsToExport.map((row) =>
        headers
          .map((h) => {
            const fieldName = headerToFieldMap[h];
            const value = row[fieldName];
            return `"${value || ""}"`;
          })
          .join(",")
      ),
    ].join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const [editedRows, setEditedRows] = useState([...scrapingHistory]);
  // duplicate of original data
  // Example pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);

  const filteredScrapingHistory = scrapingHistory.filter((entry) => {
    const matchIndustry = entry.industry
      ?.toLowerCase()
      .includes(industryFilter.toLowerCase());
    const matchCity = entry.city
      ?.toLowerCase()
      .includes(cityFilter.toLowerCase());
    const matchState = entry.state
      ?.toLowerCase()
      .includes(stateFilter.toLowerCase());
    const matchBBB = entry.bbbRating
      ?.toLowerCase()
      .includes(bbbRatingFilter.toLowerCase());
    const matchProduct = entry.productCategory
      ?.toLowerCase()
      .includes(productFilter.toLowerCase());
    const matchBusinessType = entry.businessType
      ?.toLowerCase()
      .includes(businessTypeFilter.toLowerCase());
    const matchSource = entry.source
      ?.toLowerCase()
      .includes(sourceFilter.toLowerCase());

    const {
      operation: revenueOp,
      value: revenueVal,
      upper: revenueUpper,
    } = parseFilter(revenueFilter, true);
    const rev = parseRevenue(entry.revenue);
    const matchRevenue =
      revenueVal === null
        ? true
        : revenueOp === "less than"
          ? rev < revenueVal
          : revenueOp === "greater than"
            ? rev > revenueVal
            : revenueOp === "less than or equal"
              ? rev <= revenueVal
              : revenueOp === "greater than or equal"
                ? rev >= revenueVal
                : revenueOp === "between"
                  ? rev >= revenueVal && rev <= (revenueUpper ?? revenueVal)
                  : rev === revenueVal;

    const {
      operation: empOp,
      value: empVal,
      upper: empUpper,
    } = parseFilter(employeesFilter);
    const emp = parseInt(entry.employees);
    const matchEmployees = isNaN(empVal)
      ? true
      : empOp === "less than"
        ? emp < empVal
        : empOp === "greater than"
          ? emp > empVal
          : empOp === "less than or equal"
            ? emp <= empVal
            : empOp === "greater than or equal"
              ? emp >= empVal
              : empOp === "between"
                ? emp >= empVal && emp <= (empUpper ?? empVal)
                : emp === empVal;

    const {
      operation: yearOp,
      value: yearVal,
      upper: yearUpper,
    } = parseFilter(yearFoundedFilter);
    const year = parseInt(entry.yearFounded);
    const matchYearFounded = isNaN(yearVal)
      ? true
      : yearOp === "less than"
        ? year < yearVal
        : yearOp === "greater than"
          ? year > yearVal
          : yearOp === "less than or equal"
            ? year <= yearVal
            : yearOp === "greater than or equal"
              ? year >= yearVal
              : yearOp === "between"
                ? year >= yearVal && year <= (yearUpper ?? yearVal)
                : year === yearVal;

    return (
      matchIndustry &&
      matchCity &&
      matchState &&
      matchBBB &&
      matchProduct &&
      matchBusinessType &&
      matchRevenue &&
      matchSource &&
      matchEmployees &&
      matchYearFounded
    );
  });

  // Derive indexes for slicing the filtered data
  const totalPages = Math.ceil(filteredScrapingHistory.length / itemsPerPage);
  const indexOfFirstItem = (currentPage - 1) * itemsPerPage;
  const indexOfLastItem = currentPage * itemsPerPage;
  const currentItems = filteredScrapingHistory.slice(
    indexOfFirstItem,
    indexOfLastItem
  );

  const [selectedCompanies, setSelectedCompanies] = useState([]);

  const handleSelectAll = () => {
    const visibleIds = scrapingHistory
      .slice(indexOfFirstItem, indexOfLastItem)
      .map((entry) => entry.id);

    if (selectAll) {
      setSelectedCompanies([]);
    } else {
      setSelectedCompanies(visibleIds);
    }

    setSelectAll(!selectAll);
  };

  const handleSelectCompany = (id) => {
    const updatedSelection = selectedCompanies.includes(id)
      ? selectedCompanies.filter((cid) => cid !== id)
      : [...selectedCompanies, id];

    setSelectedCompanies(updatedSelection);

    const visibleIds = scrapingHistory
      .slice(indexOfFirstItem, indexOfLastItem)
      .map((entry) => entry.id);

    setSelectAll(visibleIds.every((id) => updatedSelection.includes(id)));
  };

  // const filteredCompanies = scrapingHistory.slice(
  //   indexOfFirstItem,
  //   indexOfLastItem
  // );

  // Pie Chart: Industry Distribution
  const [pieField, setPieField] = useState('industry');
  const pieFieldOptions = [
    { value: 'industry', label: 'Industry' },
    { value: 'city', label: 'City' },
    { value: 'state', label: 'State' },
    { value: 'source', label: 'Source' },
  ];

  const getPieData = (field) => {
    const map = {};
    scrapingHistory.forEach((row) => {
      const key = (row[field] || 'Unknown').trim() || 'Unknown';
      map[key] = (map[key] || 0) + 1;
    });
    return Object.entries(map).map(([name, value]) => ({ name, value }));
  };
  const pieData = getPieData(pieField);

  // Bar Chart: Companies per City
  const [barField, setBarField] = useState('city');

  // Compute barData based on selected field
  const getBarData = (field) => {
    const map = {};
    scrapingHistory.forEach((row) => {
      const key = (row[field] || 'Unknown').trim() || 'Unknown';
      map[key] = (map[key] || 0) + 1;
    });
    return Object.entries(map).map(([name, count]) => ({ name, count }));
  };
  const barData = getBarData(barField);

  // Line Chart: Weekly Enrichment Trends
  const [trendGranularity, setTrendGranularity] = useState('day');
  const trendGranularityOptions = [
    { value: 'year', label: 'Year' },
    { value: 'month', label: 'Month' },
    { value: 'week', label: 'Week' },
    { value: 'day', label: 'Day' },
  ];

  // Compute trendData based on selected granularity
  const getTrendKey = (dateStr, granularity) => {
    const date = dayjs(dateStr);
    if (!date.isValid()) return '';
    if (granularity === 'year') return date.format('YYYY');
    if (granularity === 'month') return date.format('YYYY-MM');
    if (granularity === 'week') return date.format('YYYY-[W]WW');
    return date.format('YYYY-MM-DD');
  };
  const trendCounts = {};
  scrapingHistory.forEach(curr => {
    const rawDate = curr.created || curr.updated || new Date().toISOString();
    const key = getTrendKey(rawDate, trendGranularity);
    if (!key) return;
    trendCounts[key] = (trendCounts[key] || 0) + 1;
  });
  const trendData = Object.entries(trendCounts)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([date, count]) => ({ date, count }));

  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  // At the top of Home(), alongside your other handlers:
  const handleSortBy = (sortBy, direction) => {
    // Count how many non‐empty fields each row has:
    const getFilledCount = (row) =>
      Object.entries(row).filter(([key, value]) => {
        if (
          ["id", "lead_id", "draft_id", "sourceType"].includes(key) ||
          value === null ||
          value === undefined ||
          value === "" ||
          value === "N/A"
        ) {
          return false;
        }
        return true;
      }).length;

    // Determine the base array to sort:
    const base = [...scrapingHistory];

    // Sort by completeness only if sortBy === "filled", otherwise you can
    // extend this switch for revenue, employees, etc.:
    const sorted = base.sort((a, b) => {
      if (sortBy === "filled") {
        const aCount = getFilledCount(a);
        const bCount = getFilledCount(b);
        return direction === "most" ? bCount - aCount : aCount - bCount;
      }
      // Example: alphabetical company
      if (sortBy === "company") {
        return direction === "most"
          ? b.company.localeCompare(a.company)
          : a.company.localeCompare(b.company);
      }
      // ...add more sortBy cases here...
      return 0;
    });

    // Push the new order into state:
    setScrapingHistory(sorted);
    setEditedRows(sorted); // keep the "edited" mirror in sync
    setCurrentPage(1); // reset pagination to page 1
  };

  useEffect(() => {
    const verifyAndFetchLeads = async () => {
      try {
        setIsCheckingAuth(true);

        // 1. First verify authentication
        const authRes = await fetch(`${DATABASE_URL}/ping-auth`, {
          method: "GET",
          credentials: "include",
        });

        if (!authRes.ok) {
          console.warn("⚠️ Auth check failed, redirecting to login");
          router.push("/auth");
          return;
        }

        console.log("✅ Authentication verified");

        // 2. Fetch drafts data
        const draftsRes = await fetch(`${DATABASE_URL}/leads/drafts`, {
          // Changed endpoint
          method: "GET",
          credentials: "include",
        });

        // Handle non-OK responses
        if (!draftsRes.ok) {
          const errorText = await draftsRes.text();
          console.warn("⚠️ Drafts fetch failed:", {
            status: draftsRes.status,
            statusText: draftsRes.statusText,
            response: errorText,
          });
          return;
        }

        // Safely parse JSON
        let data = [];
        try {
          const responseText = await draftsRes.text();
          data = responseText ? JSON.parse(responseText) : [];
        } catch (parseError) {
          console.error("🚨 Failed to parse drafts response:", parseError);
          return;
        }

        // Transform data with proper error handling
        const parsed = (Array.isArray(data) ? data : []).map((entry) => {
          const draftData = entry.draft_data || {};
          return {
            id: entry.lead_id || entry.id || "",
            lead_id: entry.lead_id || entry.id || "",
            draft_id: entry.draft_id || "",
            company: draftData.company || "N/A",
            website: draftData.website || "",
            industry: draftData.industry || "",
            productCategory: draftData.product_category || "",
            businessType: draftData.business_type || "",
            employees: (() => {
              const emp = draftData.employees;
              if (!emp) return "";
              if (typeof emp === "string") return emp;
              if (typeof emp === "number") return emp.toString();
              if (typeof emp === "object" && emp.isRange) {
                return `${emp.min}-${emp.max}`;
              }
              return emp.toString();
            })(),
            revenue: draftData.revenue || "",
            yearFounded: draftData.year_founded?.toString() || "",
            bbbRating: draftData.bbb_rating || "",
            street: draftData.street || "",
            city: draftData.city || "",
            state: draftData.state || "",
            companyPhone: draftData.company_phone || "",
            companyLinkedin: draftData.company_linkedin || "",
            ownerFirstName: draftData.owner_first_name || "",
            ownerLastName: draftData.owner_last_name || "",
            ownerTitle: draftData.owner_title || "",
            ownerLinkedin: draftData.owner_linkedin || "",
            ownerPhoneNumber: draftData.owner_phone_number || "",
            ownerEmail: draftData.owner_email || "",
            source: draftData.source || "",
            created: entry.created_at
              ? new Date(entry.created_at).toLocaleString()
              : "N/A",
            updated: entry.updated_at
              ? new Date(entry.updated_at).toLocaleString()
              : "N/A",
            sourceType: "database",
          };
        });

        setScrapingHistory(parsed);
        setEditedRows(parsed);
      } catch (error) {
        console.error("🚨 Error in verifyAndFetchLeads:", {
          error: error.message,
          stack: error.stack,
        });
        router.push("/auth");
      } finally {
        setIsCheckingAuth(false);
      }
    };

    verifyAndFetchLeads();
  }, [router]); // Added router to dependency array

  useEffect(() => {
    if (!hasSorted && scrapingHistory.length > 0) {
      handleSortBy("filled", "most");
      setHasSorted(true);
    }
  }, [scrapingHistory, hasSorted]);





  const [subscriptionInfo, setSubscriptionInfo] = useState(null);

  useEffect(() => {
    const fetchSubscriptionInfo = async () => {
      try {
        const res = await axios.get(`${DATABASE_URL}/user/subscription_info`, {
          withCredentials: true,
        });

        setSubscriptionInfo(res.data);
        
        // Update session storage with the correct subscription data from API
        if (res.data?.subscription) {
          const currentUser = JSON.parse(sessionStorage.getItem("user") || "{}");
          const updatedUser = {
            ...currentUser,
            // Update credits
            credits_remaining: res.data.subscription.credits_remaining || currentUser.credits_remaining,
            // Update subscription status
            status: res.data.subscription.is_paused ? "pause" : "active",
            // Update plan/tier information
            tier: res.data.subscription.plan_name || currentUser.tier
          };
          sessionStorage.setItem("user", JSON.stringify(updatedUser));
        }
      } catch (err) {
        console.error("Error fetching subscription info:", err);
      }
    };

    fetchSubscriptionInfo();
  }, []);

  const [releaseNotes, setReleaseNotes] = useState([]);

  useEffect(() => {
    const fetchReleaseNotes = async () => {
      try {
        const res = await axios.get(`${DATABASE_URL}/release-notes`, { withCredentials: true });
        setReleaseNotes(res.data.notes || []);
        sessionStorage.setItem('releaseNotes', JSON.stringify(res.data.notes || []));
        console.log('Fetched release notes:', res.data.notes);
      } catch (err) {
        console.error('Error fetching release notes:', err);
      }
    };
    fetchReleaseNotes();
  }, []);

  // Handle clicking outside forward dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showForwardDropdown && !event.target.closest('.forward-dropdown-container')) {
        setShowForwardDropdown(false);
        setForwardStep("team");
        setSelectedTeam("");
        setSelectedProject("");
        setSelectedTask("");
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showForwardDropdown]);

  const COLORS = [
    "#1EBE8F", // More vibrant Green-Teal
    "#129C91", // Cyan shift, more pop
    "#3BA2D0", // Lighter Cyan-Blue
    "#E67E22", // Orange
    "#FFF4A4", // More vibrant Deep Blue
    "#6175FF", // Strong Violet-Blue
  ];

  useEffect(() => {
    // Subscription expiry reminder in Notif
    let user = null;
    if (typeof window !== 'undefined') {
      try {
        user = JSON.parse(sessionStorage.getItem('user') || '{}');
      } catch {}
    }
    if (user && user.subscription && user.subscription.plan_expiration_timestamp) {
      const daysLeft = dayjs(user.subscription.plan_expiration_timestamp).diff(dayjs(), 'day');
      if (daysLeft >= 0 && daysLeft <= 5) {
        showNotification(
          `Your subscription will expire in ${daysLeft} day${daysLeft !== 1 ? 's' : ''}. Please renew to avoid interruption.`,
          "info"
        );
      }
    }
  }, []);

  // Add at the top of the component (after hooks)
  const [corrX, setCorrX] = useState('city');
  const [corrGroup, setCorrGroup] = useState('industry');
  const corrFieldOptions = pieFieldOptions; // reuse

  // Compute top 5 group values for the selected grouping feature
  const groupCounts = {};
  scrapingHistory.forEach(row => {
    const key = (row[corrGroup] || 'Unknown').trim() || 'Unknown';
    groupCounts[key] = (groupCounts[key] || 0) + 1;
  });
  const topGroups = Object.entries(groupCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([name]) => name);

  // Prepare data for the grouped bar chart
  const corrDataMap = {};
  scrapingHistory.forEach(row => {
    const xVal = (row[corrX] || 'Unknown').trim() || 'Unknown';
    const groupVal = (row[corrGroup] || 'Unknown').trim() || 'Unknown';
    if (!topGroups.includes(groupVal)) return;
    if (!corrDataMap[xVal]) corrDataMap[xVal] = { [corrX]: xVal };
    corrDataMap[xVal][groupVal] = (corrDataMap[xVal][groupVal] || 0) + 1;
  });
  const corrData = Object.values(corrDataMap);

  return isCheckingAuth ? (
    <div className="fixed inset-0 bg-black bg-opacity-30 backdrop-blur-sm z-50 flex items-center justify-center pointer-events-none">
      <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-yellow-400"></div>
    </div>
  ) : (
    <>
    <FeedbackPopup />
      {/* Email-not-verified popup */}
      <Popup show={showPopup} onClose={handleClose}>
        <div className="text-center flex flex-col items-center justify-center">
          <h2 className="text-lg font-semibold">Account Not Verified</h2>
          <p className="mt-2">
            Your account hasn't been verified yet. Please check your email for
            the verification link.
          </p>

          {/* Resend Verification Button */}
          <button
            className="mt-4 px-4 py-2 rounded text-white"
            style={{ backgroundColor: "#4a90e2" }}
            onClick={async () => {
              try {
                await fetch(`${DATABASE_URL}/auth/send-verification`, {
                  method: "POST",
                  credentials: "include",
                });
                showNotification(
                  "Verification email resent. Please check your inbox.",
                  "info"
                );
              } catch (err) {
                console.error("Failed to resend verification email:", err);
                showNotification(
                  "Failed to resend verification email.",
                  "error"
                );
              }
            }}
          >
            Resend Verification Link
          </button>

          {/* OK Button */}
          <button
            className="mt-2 px-4 py-2 rounded text-white"
            style={{ backgroundColor: "#7bc3a4" }}
            onClick={handleClose}
          >
            OK
          </button>
        </div>
      </Popup>

      {/* Main app content */}
      <main className="px-20 py-16 space-y-10">
        <div className="text-2xl font-semibold text-foreground text-white">
          Hi, {user.username || "there"}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          {[
            {
              label: "Total Leads",
              value: scrapingHistory.length.toLocaleString(),
              iconBg: "bg-teal-900 group-hover:bg-yellow-400",
              iconText: "text-white group-hover:text-black",
            },
            {
              label: "Remaining Credits",
              value: (() => {
                // Get credits from subscription info API
                const apiCredits = subscriptionInfo?.subscription?.credits_remaining ?? 0;
                return apiCredits.toLocaleString();
              })(),
              change: "",
              comparison: "",
              iconBg: "bg-teal-900 group-hover:bg-yellow-400",
              iconText: "text-white group-hover:text-black",
            },
            {
              label: "Subscription",
              value: subscriptionInfo?.subscription?.plan_name
                ? `${subscriptionInfo.subscription.plan_name} Plan`
                : "N/A",
              change: subscriptionInfo?.subscription?.is_paused
                ? "Paused"
                : "Active",
                               comparison: subscriptionInfo?.subscription?.is_paused
     ? (
       subscriptionInfo?.subscription?.pause_end_date
         ? `until ${new Date(subscriptionInfo.subscription.pause_end_date).toLocaleDateString()}`
         : "Paused"
     )
     : (
       // Only show expiration date for non-free plans
       subscriptionInfo?.subscription?.plan_name?.toLowerCase() === "free" 
         ? ""
         : (
           subscriptionInfo?.subscription?.plan_expiration_timestamp
             ? `until ${new Date(subscriptionInfo.subscription.plan_expiration_timestamp).toLocaleDateString()}`
             : "Expiration unknown"
         )
     ),
              action: {
                label: "Upgrade",
                onClick: () => router.push("/subscription")
              },
              iconBg: "bg-teal-900 group-hover:bg-yellow-400",
              iconText: "text-white group-hover:text-black",
            },
          ].map((stat, index) => (
            <Card
              key={index}
              className={`
                relative rounded-2xl border border-[#23263a] bg-gradient-to-br from-[#181c2a] to-[#23263a]
                shadow-lg transition-transform duration-200 hover:scale-[1.025] hover:shadow-2xl
                px-8 py-7 flex flex-col justify-between min-h-[13rem] group
                overflow-hidden
              `}
            >
              {/* Accent bar */}
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-teal-400 to-purple-500 opacity-60 group-hover:opacity-90 transition-opacity" />
              {/* Title at top-left, inside colored square bg (no icon) */}
              <div className={`absolute top-5 left-5 flex items-center gap-2 px-4 h-14 rounded-lg shadow-md transition-colors duration-200 ${stat.iconBg} ${stat.iconText}`}
                style={{zIndex:2, minWidth:'max-content'}}>
                <span className="text-xl font-bold ml-2">{stat.label}</span>
              </div>
              {/* Centered content below the title bar */}
              <div className="flex flex-1 flex-col items-center justify-center min-h-[10rem]"
                style={{marginTop: '3.5rem'}}>
                <CardTitle className="text-4xl sm:text-5xl font-extrabold text-white leading-snug break-words whitespace-normal tracking-tight text-center mt-2">
                  {stat.value}
                </CardTitle>
                {/* For Subscription card, show button below value */}
                {stat.label === "Subscription" && (
                  <div className="flex flex-col gap-2 mt-4 w-full items-center">
                    {user?.status === "pause" ? (
                      /* Show Reactivate button if user status is paused */
                      <Button
                        size="sm"
                        className="text-sm px-4 py-1.5 font-semibold w-48 bg-[#4CAF50] hover:bg-[#388e3c] text-white"
                        onClick={handleReactivateSubscription}
                      >
                        Reactivate Subscription
                      </Button>
                    ) : (
                      /* Show Upgrade button for all other cases */
                      <Button
                        size="sm"
                        className="text-sm px-4 py-1.5 font-semibold w-40"
                        onClick={stat.action?.onClick}
                      >
                        {stat.action?.label}
                      </Button>
                    )}
                  </div>
                )}
                <CardContent className="pt-4 text-[15px] text-white font-medium flex flex-col items-center gap-1 w-full">
                  <span>{stat.change}</span>
                  <span className="text-muted-foreground">{stat.comparison}</span>
                </CardContent>
              </div>
            </Card>
          ))}
        </div>

        {/* Analytic Cards - Modern Style */}
        <div className="grid grid-cols-1 gap-6">
          {/* Industry Distribution - full width, pie chart + top 5 industries */}
          <Card
            className={`
              relative rounded-2xl border border-[#23263a] bg-gradient-to-br from-[#181c2a] to-[#23263a]
              shadow-lg transition-transform duration-200 hover:scale-[1.025] hover:shadow-2xl
              px-8 py-7 flex flex-col justify-between min-h-[13rem] group
              overflow-hidden w-full
            `}
          >
            {/* Accent bar */}
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-teal-400 to-purple-500 opacity-60 group-hover:opacity-90 transition-opacity" />
            {/* Title at top-left, inside colored square bg (no icon) - unified color */}
            <div className={`absolute top-5 left-5 flex items-center gap-2 px-4 h-14 rounded-lg shadow-md transition-colors duration-200 bg-teal-900 group-hover:bg-yellow-400 text-white group-hover:text-black`}
              style={{zIndex:2, minWidth:'max-content'}}>
              <span className="text-xl font-bold ml-2">{pieFieldOptions.find(opt => opt.value === pieField)?.label} Distribution</span>
            </div>
            {/* Content: Pie chart + Top 5 industries */}
            <div className="flex flex-1 flex-row items-center justify-center w-full" style={{marginTop: '3.5rem', minHeight: 250}}>
              <div className="flex-1 flex justify-center">
                <ResponsiveContainer width="100%" height={250}>
                  <PieChart>
                    <Pie
                      data={pieData.slice().sort((a, b) => b.value - a.value).slice(0, 15)}
                      dataKey="value"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      outerRadius={80}
                    >
                      {pieData.slice().sort((a, b) => b.value - a.value).slice(0, 15).map((entry, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={COLORS[index % COLORS.length]}
                        />
                      ))}
                    </Pie>
                    <RechartTooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              {/* Top 5 industries list */}
              <div className="flex-1 flex flex-col justify-center items-start pl-8">
                <div className="text-lg font-bold text-white mb-2">Top 5 {(() => {
                  const label = pieFieldOptions.find(opt => opt.value === pieField)?.label;
                  if (label === 'City') return 'Cities';
                  if (label === 'Industry') return 'Industries';
                  if (label === 'State') return 'States';
                  if (label === 'Source') return 'Sources';
                  return label + 's';
                })()}</div>
                <ul className="w-full space-y-2">
                  {pieData
                    .slice()
                    .sort((a, b) => b.value - a.value)
                    .slice(0, 5)
                    .map((item, idx) => (
                      <li key={item.name} className="flex items-center gap-3">
                        <span className="inline-block w-3 h-3 rounded-full" style={{background: COLORS[idx % COLORS.length]}}></span>
                        <span className="font-semibold text-white">{item.name}</span>
                        <span className="ml-auto text-blue-300 font-mono">{item.value}</span>
                      </li>
                    ))}
                </ul>
              </div>
            </div>
            {/* Dropdown at the top right */}
            <div className="absolute top-5 right-5 z-10">
              <Select value={pieField} onValueChange={setPieField}>
                <SelectTrigger className="w-[140px]">
                  <SelectValue>{pieFieldOptions.find(opt => opt.value === pieField)?.label}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {pieFieldOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </Card>

          {/* Companies by City - full width */}
          <Card
            className={`
              relative rounded-2xl border border-[#23263a] bg-gradient-to-br from-[#181c2a] to-[#23263a]
              shadow-lg transition-transform duration-200 hover:scale-[1.025] hover:shadow-2xl
              px-8 py-7 flex flex-col justify-between min-h-[13rem] group
              overflow-hidden w-full
            `}
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-teal-400 to-purple-500 opacity-60 group-hover:opacity-90 transition-opacity" />
            <div className={`absolute top-5 left-5 flex items-center gap-2 px-4 h-14 rounded-lg shadow-md transition-colors duration-200 bg-teal-900 group-hover:bg-yellow-400 text-white group-hover:text-black`}
              style={{zIndex:2, minWidth:'max-content'}}>
              <span className="text-xl font-bold ml-2">{corrFieldOptions.find(opt => opt.value === corrX)?.label} vs. {corrFieldOptions.find(opt => opt.value === corrGroup)?.label}</span>
            </div>
            {/* Dropdowns at the top right */}
            <div className="absolute top-5 right-5 z-10 flex gap-2">
              <Select value={corrX} onValueChange={setCorrX}>
                <SelectTrigger className="w-[120px]"><SelectValue>{corrFieldOptions.find(opt => opt.value === corrX)?.label}</SelectValue></SelectTrigger>
                <SelectContent>
                  {corrFieldOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={corrGroup} onValueChange={setCorrGroup}>
                <SelectTrigger className="w-[120px]"><SelectValue>{corrFieldOptions.find(opt => opt.value === corrGroup)?.label}</SelectValue></SelectTrigger>
                <SelectContent>
                  {corrFieldOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-1 flex-col items-center justify-center w-full" style={{marginTop: '3.5rem', minHeight: 250}}>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={corrData.slice().sort((a, b) => {
                  // Sort by total count descending
                  const aSum = topGroups.reduce((sum, g) => sum + (a[g] || 0), 0);
                  const bSum = topGroups.reduce((sum, g) => sum + (b[g] || 0), 0);
                  return bSum - aSum;
                }).slice(0, 15)}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey={corrX} />
                  <YAxis />
                  <RechartTooltip />
                  {topGroups.map((group, idx) => (
                    <Bar key={group} dataKey={group} fill={COLORS[idx % COLORS.length]} />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Weekly Growth Trend - full width */}
          <Card
            className={`
              relative rounded-2xl border border-[#23263a] bg-gradient-to-br from-[#181c2a] to-[#23263a]
              shadow-lg transition-transform duration-200 hover:scale-[1.025] hover:shadow-2xl
              px-8 py-7 flex flex-col justify-between min-h-[13rem] group
              overflow-hidden w-full
            `}
          >
            <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-teal-400 to-purple-500 opacity-60 group-hover:opacity-90 transition-opacity" />
            <div className={`absolute top-5 left-5 flex items-center gap-2 px-4 h-14 rounded-lg shadow-md transition-colors duration-200 bg-teal-900 group-hover:bg-yellow-400 text-white group-hover:text-black`}
              style={{zIndex:2, minWidth:'max-content'}}>
              <span className="text-xl font-bold ml-2">Total Leads</span>
            </div>
            <div className="flex flex-1 flex-col items-center justify-center w-full" style={{marginTop: '3.5rem', minHeight: 250}}>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={trendData}>
                  <XAxis dataKey="date" />
                  <YAxis />
                  <RechartTooltip />
                  <Legend />
                  <Line type="monotone" dataKey="count" stroke="#8884d8" />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <div className="absolute top-5 right-5 z-10">
              <Select value={trendGranularity} onValueChange={setTrendGranularity}>
                <SelectTrigger className="w-[120px]">
                  <SelectValue>{trendGranularityOptions.find(opt => opt.value === trendGranularity)?.label}</SelectValue>
                </SelectTrigger>
                <SelectContent>
                  {trendGranularityOptions.map(opt => (
                    <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </Card>
        </div>

        {/* History Table */}
        <div className="mt-10">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Leads History</CardTitle>
                <div className="flex items-center gap-4">
                  {/* Search Bar */}
                  <div className="relative">
                    <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="search"
                      placeholder="Search history…"
                      className="w-80 pl-8"
                      value={searchTerm}
                      onChange={(e) => setSearchTerm(e.target.value)}
                    />
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2">
                    <SortDropdown onApply={handleSortBy} />

                    <Button
                      variant="outline"
                      size="icon"
                      onClick={() => setShowFilters(f => !f)}
                      title={showFilters ? "Hide Filters" : "Show Filters"}
                    >
                      <Filter className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="icon"
                      onClick={handleExportCSVWithCredits}
                      title={selectedCompanies.length > 0 ? `Export ${selectedCompanies.length} selected items` : "Select items to export"}
                      // disabled={selectedCompanies.length === 0}
                      className={`relative ${selectedCompanies.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
                    >
                      <Download className="h-4 w-4" />
                      {selectedCompanies.length > 0 && (
                        <span className="absolute -top-2 -right-2 text-xs bg-blue-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                          {selectedCompanies.length}
                        </span>
                      )}
                    </Button>
                    <div className="relative">
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={handleForwardClick}
                        title={selectedCompanies.length > 0 ? `Forward ${selectedCompanies.length} selected items` : "Select items to forward"}
                        className={`relative ${selectedCompanies.length === 0 ? "opacity-50 cursor-not-allowed" : ""}`}
                      >
                        <Forward className="h-4 w-4" />
                        {selectedCompanies.length > 0 && (
                          <span className="absolute -top-2 -right-2 text-xs bg-green-500 text-white rounded-full px-1.5 py-0.5 min-w-[1.2rem] flex items-center justify-center">
                            {selectedCompanies.length}
                          </span>
                        )}
                      </Button>
                      
                      {/* Forward Dropdown */}
                      {showForwardDropdown && (
                        <div className="forward-dropdown-container absolute top-full right-0 mt-2 w-64 bg-dark-secondary border border-dark rounded-lg shadow-lg z-50">
                          <div className="p-3 border-b border-dark">
                            <h3 className="text-sm font-semibold text-dark-primary">Forward to Task</h3>
                            <p className="text-xs text-dark-muted">Select team, project, and task</p>
                          </div>
                          
                          <div className="p-3">
                            {forwardStep === "team" && (
                              <div>
                                <label className="block text-sm font-medium text-dark-primary mb-2">Select Team</label>
                                {console.log("Teams state in render:", teams, "Length:", teams.length)}
                                {isLoadingForward ? (
                                  <div className="text-sm text-dark-muted">Loading teams...</div>
                                ) : teams.length === 0 ? (
                                  <div className="text-sm text-dark-muted">No teams available</div>
                                ) : (
                                                                       <div className="space-y-1 max-h-32 overflow-y-auto">
                                       {console.log("Rendering teams:", teams)}
                                       {teams.map((workspace) => {
                                         console.log("Rendering workspace:", workspace);
                                         return (
                                           <button
                                             key={workspace.workspace_id}
                                             onClick={() => handleTeamSelect(workspace.workspace_id)}
                                             className="w-full text-left px-3 py-2 text-sm hover:bg-dark-hover rounded-md transition-colors text-dark-primary"
                                           >
                                             <div className="font-medium">{workspace.name}</div>
                                             <div className="text-xs text-blue-400 italic">{workspace.user_role}</div>
                                           </button>
                                         );
                                       })}
                                     </div>
                                )}
                              </div>
                            )}
                            
                            {forwardStep === "project" && (
                              <div>
                                <div className="flex items-center justify-between mb-2">
                                  <label className="block text-sm font-medium text-dark-primary">Select Project</label>
                                  <button
                                    onClick={() => {
                                      setForwardStep("team");
                                      setSelectedTeam("");
                                    }}
                                    className="text-xs text-blue-400 hover:text-blue-300"
                                  >
                                    ← Back to Teams
                                  </button>
                                </div>
                                {isLoadingForward ? (
                                  <div className="text-sm text-dark-muted">Loading projects...</div>
                                ) : projects.length === 0 ? (
                                  <div className="text-sm text-dark-muted">No projects available in this team</div>
                                ) : (
                                  <div className="space-y-1 max-h-32 overflow-y-auto">
                                    {projects.map((project) => (
                                      <button
                                        key={project.project_id}
                                        onClick={() => handleProjectSelect(project.project_id)}
                                        className="w-full text-left px-3 py-2 text-sm hover:bg-dark-hover rounded-md transition-colors text-dark-primary"
                                      >
                                        <div className="font-medium">{project.name}</div>
                                        <div className="text-xs text-dark-muted">{project.description}</div>
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                            
                            {forwardStep === "task" && (
                              <div>
                                <div className="flex items-center justify-between mb-2">
                                  <label className="block text-sm font-medium text-dark-primary">Select Task</label>
                                  <button
                                    onClick={() => {
                                      setForwardStep("project");
                                      setSelectedProject("");
                                    }}
                                    className="text-xs text-blue-400 hover:text-blue-300"
                                  >
                                    ← Back to Projects
                                  </button>
                                </div>
                                {isLoadingForward ? (
                                  <div className="text-sm text-dark-muted">Loading tasks...</div>
                                ) : tasks.length === 0 ? (
                                  <div className="text-sm text-dark-muted">No tasks available in this project</div>
                                ) : (
                                  <div className="space-y-1 max-h-32 overflow-y-auto">
                                    {tasks.map((task) => (
                                      <button
                                        key={task.task_id}
                                        onClick={() => handleTaskSelect(task.task_id)}
                                        className="w-full text-left px-3 py-2 text-sm hover:bg-dark-hover rounded-md transition-colors text-dark-primary"
                                      >
                                        <div className="font-medium">{task.title}</div>
                                        <div className="text-xs text-dark-muted">{task.description}</div>
                                      </button>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Filter Section */}
              {showFilters && (
                <div className="flex flex-wrap gap-4 my-4">
                  <Input
                    placeholder="Industry"
                    value={industryFilter}
                    onChange={(e) => setIndustryFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Product/Service Category"
                    value={productFilter}
                    onChange={(e) => setProductFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Business Type"
                    value={businessTypeFilter}
                    onChange={(e) => setBusinessTypeFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Employees Count"
                    value={employeesFilter}
                    onChange={(e) => setEmployeesFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Revenue"
                    value={revenueFilter}
                    onChange={(e) => setRevenueFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Year Founded"
                    value={yearFoundedFilter}
                    onChange={(e) => setYearFoundedFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="BBB Rating"
                    value={bbbRatingFilter}
                    onChange={(e) => setBbbRatingFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="City"
                    value={cityFilter}
                    onChange={(e) => setCityFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="State"
                    value={stateFilter}
                    onChange={(e) => setStateFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Input
                    placeholder="Source"
                    value={sourceFilter}
                    onChange={(e) => setSourceFilter(e.target.value)}
                    className="w-[240px]"
                  />
                  <Button variant="ghost" size="sm" onClick={clearAllFilters}>
                    <X className="h-4 w-4 mr-1" />
                    Clear All
                  </Button>
                </div>
              )}
            </CardHeader>

            <CardContent>
              {/* Scrollable container with a max height */}
              <div className="w-full overflow-x-auto relative border rounded-md">
                <Table className="min-w-full text-sm ">
                  <TableHeader>
                    <TableRow>
                      {/* Sticky Checkbox Column */}
                      <TableHead className="sticky top-0 left-0 z-40 bg-background px-6 py-3 w-12 text-base font-bold text-white">
                        <Checkbox
                          checked={selectAll}
                          onCheckedChange={handleSelectAll}
                        />
                      </TableHead>

                      {/* Sticky Company Column */}
                      <TableHead className="sticky top-0 left-12 z-30 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap min-w-[200px] border-r">
                        Company
                      </TableHead>

                      {/* Remaining Headers */}
                      {[
                        "Website",
                        "Industry",
                        "Product/Service Category",
                        "Business Type (B2B, B2B2C)",
                        "Employees Count",
                        "Revenue",
                        "Year Founded",
                        "BBB Rating",
                        "Street",
                        "City",
                        "State",
                        "Company Phone",
                        "Company LinkedIn",
                        "Owner's First Name",
                        "Owner's Last Name",
                        "Owner's Title",
                        "Owner's LinkedIn",
                        "Owner's Phone Number",
                        "Owner's Email",
                        "Source",
                        "Created Date",
                        "Updated",
                        "Actions",
                      ].map((label, i) => (
                        <TableHead
                          key={i}
                          className="sticky top-0 z-20 bg-background text-base font-bold text-white px-6 py-3 whitespace-nowrap"
                        >
                          {label}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>

                  <tbody>
                    {currentItems.map((row, i) => (
                      <TableRow key={i} className="border-t">
                        {/* Sticky Checkbox Column */}
                        <TableCell className="sticky left-0 z-20 bg-inherit px-6 py-2 w-12">
                          <Checkbox
                            checked={selectedCompanies.includes(row.id)}
                            onCheckedChange={() => handleSelectCompany(row.id)}
                          />
                        </TableCell>

                        {/* Sticky Company Column */}
                        <TableCell className="sticky left-12 z-10 bg-inherit px-6 py-2 max-w-[240px] align-top border-r">
                          {editingRowIndex === i ? (
                            <input
                              type="text"
                              className="w-full bg-transparent border-b border-muted focus:outline-none text-sm"
                              value={editedRows[i]?.company ?? ""}
                              onChange={(e) =>
                                handleFieldChange(i, "company", e.target.value)
                              }
                            />
                          ) : (
                            <ExpandableCell text={row.company || "N/A"} />
                          )}
                        </TableCell>

                        {/* Remaining Cells */}
                        {[
                          "website",
                          "industry",
                          "productCategory",
                          "businessType",
                          "employees",
                          "revenue",
                          "yearFounded",
                          "bbbRating",
                          "street",
                          "city",
                          "state",
                          "companyPhone",
                          "companyLinkedin",
                          "ownerFirstName",
                          "ownerLastName",
                          "ownerTitle",
                          "ownerLinkedin",
                          "ownerPhoneNumber",
                          "ownerEmail",
                          "source",
                          "created",
                          "updated",
                        ].map((field) => {
                          const rawValue = row[field];
                          const displayValue =
                            rawValue === null ||
                              rawValue === undefined ||
                              rawValue === ""
                              ? "N/A"
                              : rawValue;

                          const isUrl =
                            typeof rawValue === "string" &&
                            (rawValue.startsWith("http://") ||
                              rawValue.startsWith("https://"));

                          const shortened =
                            isUrl && rawValue.length > 0
                              ? rawValue
                                .replace(/^https?:\/\//, "")
                                .replace(/^www\./, "")
                                .split("/")[0]
                              : displayValue;

                          return (
                            <TableCell
                              key={field}
                              className="px-6 py-2 max-w-[240px] align-top"
                            >
                              {editingRowIndex === i ? (
                                <input
                                  type="text"
                                  className="w-full bg-transparent border-b border-muted focus:outline-none text-sm"
                                  value={editedRows[i]?.[field] ?? ""}
                                  onChange={(e) =>
                                    handleFieldChange(i, field, e.target.value)
                                  }
                                />
                              ) : isUrl ? (
                                <a
                                  href={rawValue}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-blue-600 underline hover:text-blue-800 block truncate"
                                  title={rawValue}
                                >
                                  {shortened}
                                </a>
                              ) : (
                                <ExpandableCell text={displayValue} />
                              )}
                            </TableCell>
                          );
                        })}

                        {/* Action Column */}
                        <TableCell className="px-6 py-2">
                          {editingRowIndex === i ? (
                            <>
                              <span
                                className="text-green-500 hover:underline cursor-pointer mr-2"
                                onClick={() => handleSave(i)}
                              >
                                Save
                              </span>
                              <span
                                className="text-red-500 hover:underline cursor-pointer"
                                onClick={() => handleDiscard(i)}
                              >
                                Discard
                              </span>
                            </>
                          ) : (
                            <span
                              className="text-blue-500 hover:underline cursor-pointer mr-2"
                              onClick={() => setEditingRowIndex(i)}
                            >
                              Edit
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </tbody>
                </Table>
              </div>

              {/* Pagination at the bottom */}
              {filteredScrapingHistory.length > 0 && (
                <div className="flex flex-col md:flex-row justify-between items-center mt-4 gap-4 px-4 py-2">
                  <div className="text-sm text-muted-foreground">
                    Showing {indexOfFirstItem + 1}–
                    {Math.min(indexOfLastItem, scrapingHistory.length)} of{" "}
                    {scrapingHistory.length} results
                    {selectedCompanies.length > 0 && (
                      <span className="ml-2 text-blue-600">
                        ({selectedCompanies.length} selected)
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-3 px-3 py-2">
                    <Select
                      value={itemsPerPage.toString()}
                      onValueChange={(value) => {
                        setItemsPerPage(Number(value));
                        setCurrentPage(1);
                      }}
                    >
                      <SelectTrigger className="w-[120px]">
                        <SelectValue placeholder="Items per page" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="25">25 per page</SelectItem>
                        <SelectItem value="50">50 per page</SelectItem>
                        <SelectItem value="100">100 per page</SelectItem>
                      </SelectContent>
                    </Select>

                    <Pagination>
                      <PaginationContent>
                        <PaginationItem>
                          <PaginationPrevious
                            onClick={() => setCurrentPage((p) => Math.max(p - 1, 1))}
                            aria-disabled={currentPage === 1}
                            className={
                              currentPage === 1
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                          />
                        </PaginationItem>

                        {Array.from({ length: totalPages }, (_, i) => i + 1)
                          .filter((page) => {
                            // show all if totalPages <= 7
                            if (totalPages <= 7) return true;

                            // show first, last, current, and neighbors
                            return (
                              page === 1 ||
                              page === totalPages ||
                              Math.abs(page - currentPage) <= 1
                            );
                          })
                          .reduce((acc, page, i, arr) => {
                            if (i > 0 && page - arr[i - 1] > 1) {
                              acc.push("ellipsis");
                            }
                            acc.push(page);
                            return acc;
                          }, [])
                          .map((page, idx) => (
                            <PaginationItem key={idx}>
                              {page === "ellipsis" ? (
                                <PaginationEllipsis />
                              ) : (
                                <PaginationLink
                                  isActive={page === currentPage}
                                  onClick={() => setCurrentPage(page)}
                                  className={`px-3 py-1 rounded-md text-sm font-medium ${page === currentPage
                                    ? " text-black" // active teal background
                                    : "text-black hover:bg-muted"
                                    }`}
                                >
                                  {page}
                                </PaginationLink>
                              )}
                            </PaginationItem>
                          ))}

                        <PaginationItem>
                          <PaginationNext
                            onClick={() =>
                              setCurrentPage((p) => Math.min(p + 1, totalPages))
                            }
                            aria-disabled={currentPage === totalPages}
                            className={
                              currentPage === totalPages
                                ? "pointer-events-none opacity-50"
                                : ""
                            }
                          />
                        </PaginationItem>
                      </PaginationContent>
                    </Pagination>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
        <div className="flex justify-end mt-3 gap-3">
          <Notif
            show={notif.show}
            message={notif.message}
            type={notif.type}
            onClose={() => setNotif((prev) => ({ ...prev, show: false }))}
          />
        </div>
      </main>
      <Footer />
      {subscriptionInfo?.subscription?.is_call_outreach_cust &&
        !subscriptionInfo?.subscription?.is_scheduled_for_cancellation && (
          <div className="my-6 flex justify-center">
            <Button
              className="bg-[#007BFF] hover:bg-[#0056b3] text-white font-semibold"
              onClick={() => {
                // Open links in new tabs
                window.open(
                  "https://calendar.app.google/45wvqajrQqNCpdPg6",
                  "_blank"
                );
                window.open("https://forms.gle/QzE1B9iDYJKVArnr6", "_blank");
                setShowConfirmModal(true);
              }}
            >
              Outreach Appointment
            </Button>
          </div>
        )}
      {showConfirmModal && (
        <Popup show={true} onClose={() => setShowConfirmModal(false)}>
          <div className="text-center">
            <h2 className="text-lg font-semibold mb-2">
              Have you scheduled your appointment?
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">
              You can only do this once, so please confirm.
            </p>
            <div className="flex justify-center gap-4">
              <Button
                variant="outline"
                onClick={() => setShowConfirmModal(false)}
              >
                No
              </Button>
              <Button
                className="bg-green-600 hover:bg-green-700 text-white"
                onClick={async () => {
                  try {
                    const res = await fetch(
                      `${DATABASE_URL}/subscription/confirm_appointment`,
                      {
                        method: "POST",
                        credentials: "include",
                      }
                    );
                    if (res.ok) {
                      setShowConfirmModal(false);
                      showNotification("Appointment confirmed!", "success");
                    } else {
                      showNotification(
                        "Failed to confirm appointment",
                        "error"
                      );
                    }
                  } catch (err) {
                    console.error("Error confirming appointment:", err);
                    showNotification("Unexpected error", "error");
                  }
                }}
              >
                Yes, I Did
              </Button>
            </div>
          </div>
        </Popup>
      )}
    </>
  );
}
