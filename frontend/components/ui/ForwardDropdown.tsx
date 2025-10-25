"use client";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Forward } from "lucide-react";
import axios from "axios";

const DATABASE_URL = process.env.NEXT_PUBLIC_DATABASE_URL;

interface ForwardDropdownProps {
  selectedCompanies: string[];
  onForwardComplete: () => void;
  onNotification: (message: string, type: "success" | "error" | "info") => void;
  scrapingHistory: any[];
}

export default function ForwardDropdown({
  selectedCompanies,
  onForwardComplete,
  onNotification,
  scrapingHistory,
}: ForwardDropdownProps) {
  // Forward functionality state
  const [showForwardDropdown, setShowForwardDropdown] = useState(false);
  const [teams, setTeams] = useState<any[]>([]);
  const [projects, setProjects] = useState<any[]>([]);
  const [tasks, setTasks] = useState<any[]>([]);
  const [selectedTeam, setSelectedTeam] = useState("");
  const [selectedProject, setSelectedProject] = useState("");
  const [selectedTask, setSelectedTask] = useState("");
  const [forwardStep, setForwardStep] = useState("team"); // "team", "project", "task"
  const [isLoadingForward, setIsLoadingForward] = useState(false);

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
      onNotification("Failed to fetch teams", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const fetchProjects = async (teamId: string) => {
    try {
      setIsLoadingForward(true);
      const response = await axios.get(`${DATABASE_URL}/workspace/${teamId}/projects`, {
        withCredentials: true,
      });
      setProjects(response.data.projects || []);
    } catch (error) {
      console.error("Error fetching projects:", error);
      onNotification("Failed to fetch projects", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const fetchTasks = async (teamId: string, projectId: string) => {
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
      onNotification("Failed to fetch tasks", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  const handleForwardClick = () => {
    if (selectedCompanies.length === 0) {
      onNotification("Please select at least one lead to forward", "info");
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

  const handleTeamSelect = (workspaceId: string) => {
    setSelectedTeam(workspaceId);
    setForwardStep("project");
    setSelectedProject("");
    setSelectedTask("");
    fetchProjects(workspaceId);
  };

  const handleProjectSelect = (projectId: string) => {
    setSelectedProject(projectId);
    setForwardStep("task");
    setSelectedTask("");
    fetchTasks(selectedTeam, projectId);
  };

  const handleTaskSelect = async (taskId: string) => {
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
      
      onNotification(`Successfully forwarded ${selectedCompanies.length} leads to selected task`, "success");
      setShowForwardDropdown(false);
      setForwardStep("team");
      setSelectedTeam("");
      setSelectedProject("");
      setSelectedTask("");
      onForwardComplete();
    } catch (error) {
      console.error("Error forwarding leads:", error);
      onNotification("Failed to forward leads to task", "error");
    } finally {
      setIsLoadingForward(false);
    }
  };

  // Handle clicking outside forward dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (showForwardDropdown && !(event.target as Element).closest('.forward-dropdown-container')) {
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

  return (
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
                {isLoadingForward ? (
                  <div className="text-sm text-dark-muted">Loading teams...</div>
                ) : teams.length === 0 ? (
                  <div className="text-sm text-dark-muted">No teams available</div>
                ) : (
                  <div className="space-y-1 max-h-32 overflow-y-auto">
                    {teams.map((workspace: any) => (
                      <button
                        key={workspace.workspace_id}
                        onClick={() => handleTeamSelect(workspace.workspace_id)}
                        className="w-full text-left px-3 py-2 text-sm hover:bg-dark-hover rounded-md transition-colors text-dark-primary"
                      >
                        <div className="font-medium">{workspace.name}</div>
                        <div className="text-xs text-blue-400 italic">{workspace.user_role}</div>
                      </button>
                    ))}
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
                    {projects.map((project: any) => (
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
                    {tasks.map((task: any) => (
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
  );
}
