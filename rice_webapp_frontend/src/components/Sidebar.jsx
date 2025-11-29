import { useState, useEffect } from "react";
import "../styles/Sidebar.css";
import { useNavigate, useLocation } from "react-router-dom";
import { IoMdAnalytics } from "react-icons/io";
import { FaFileAlt } from "react-icons/fa";
import { RiQrScan2Line, RiDeleteBin6Line } from "react-icons/ri";
import { CiSettings } from "react-icons/ci";
import { MdExpandMore, MdChevronRight } from "react-icons/md";

const Sidebar = ({ showSidebar, setShowSidebar }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [data, setData] = useState({ varieties: [] });
  const [expandedVarieties, setExpandedVarieties] = useState({});
  const [settingsExpanded, setSettingsExpanded] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    if (settingsExpanded) {
      loadData();
    }
  }, [settingsExpanded]);

  useEffect(() => {
    const handleDataUpdate = () => {
      loadData();
    };

    window.addEventListener('dataUpdated', handleDataUpdate);

    return () => {
      window.removeEventListener('dataUpdated', handleDataUpdate);
    };
  }, []);

  const loadData = async () => {
    try {
      const response = await fetch('/varieties');
      if (response.ok) {
        const data = await response.json();
        setData(data);
      } else {
        setData({ varieties: [] });
      }
    } catch (error) {
      console.error("Error loading data:", error);
      setData({ varieties: [] });
    }
  };

  const saveData = async (newData) => {
    try {
      const response = await fetch('/varieties', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newData),
      });

      if (response.ok) {
        setData(newData);
      } else {
        console.error("Error saving data");
      }
    } catch (error) {
      console.error("Error saving data:", error);
    }
  };

  const toggleSideBar = () => {
    setShowSidebar(!showSidebar);
  };

  const toggleSettings = (e) => {
    e.stopPropagation();
    setSettingsExpanded(!settingsExpanded);
  };

  const toggleVariety = (varietyName, e) => {
    e.stopPropagation();
    setExpandedVarieties(prev => ({
      ...prev,
      [varietyName]: !prev[varietyName]
    }));
  };

  const deleteVariety = async (varietyName, e) => {
    e.stopPropagation();
    if (window.confirm(`Delete "${varietyName}" and all its sub-varieties?`)) {
      try {
        const response = await fetch(`/varieties/${encodeURIComponent(varietyName)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          const newData = {
            ...data,
            varieties: data.varieties.filter(v => v.name !== varietyName)
          };
          setData(newData);
        } else {
          console.error("Failed to delete variety");
        }
      } catch (error) {
        console.error("Error deleting variety:", error);
      }
    }
  };

  const deleteSubVariety = async (varietyName, subVarietyName, e) => {
    e.stopPropagation();
    if (window.confirm(`Delete sub-variety "${subVarietyName}"?`)) {
      try {
        const response = await fetch(`/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(subVarietyName)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          const newData = { ...data };
          const variety = newData.varieties.find(v => v.name === varietyName);
          if (variety) {
            variety.subVarieties = variety.subVarieties.filter(s => s.name !== subVarietyName);
            setData(newData);
          }
        } else {
          console.error("Failed to delete sub-variety");
        }
      } catch (error) {
        console.error("Error deleting sub-variety:", error);
      }
    }
  };

  const authenticatedMenuItems = [
    {
      label: "New Scan",
      icon: <RiQrScan2Line />,
      path: "/upload",
      onClick: () => {
        navigate("/upload");
      },
    },
    {
      label: "Scan Analysis",
      icon: <IoMdAnalytics />,
      path: "/results",
      onClick: () => {
        navigate("/results");
      },
    },
    {
      label: "Report",
      icon: <FaFileAlt />,
      path: "/report",
      onClick: () => {
        navigate("/report");
      },
    },
  ];

  const handleItemClick = (item) => {
    if (item.onClick) {
      item.onClick();
    } else {
      navigate(item.path);
    }
  };

  return (
    <>
      {showSidebar && window.innerWidth <= 768 && (
        <div className="sidebar-overlay show" onClick={toggleSideBar}></div>
      )}

      <aside className={`result-sidebar ${showSidebar ? "expanded" : "collapsed"}`}>
        <ul className="sidebar-menu">
          {authenticatedMenuItems.map((item, index) => (
            <li
              key={index}
              className={location.pathname === item.path ? "active" : ""}
              onClick={() => handleItemClick(item)}
            >
              {item.icon}
              <span className="label">{item.label}</span>
            </li>
          ))}

          {/* Settings with expandable varieties */}
          <li
            className={`settings-item ${location.pathname === "/settings" ? "active" : ""}`}
            onClick={() => navigate("/settings")}
          >
            <CiSettings />
            <span className="label">Settings</span>
            {showSidebar && (
              <span className="expand-arrow" onClick={toggleSettings}>
                {settingsExpanded ? <MdExpandMore /> : <MdChevronRight />}
              </span>
            )}
          </li>

          {/* Varieties list */}
          {showSidebar && settingsExpanded && (
            <div className="varieties-sidebar-list">
              {data.varieties.length === 0 ? (
                <div className="no-varieties-message">
                  No varieties
                </div>
              ) : (
                data.varieties.map((variety, idx) => (
                  <div key={idx} className="variety-sidebar-item">
                    <div className="variety-sidebar-header">
                      <span
                        className="variety-expand"
                        onClick={(e) => toggleVariety(variety.name, e)}
                      >
                        {expandedVarieties[variety.name] ?
                          <MdExpandMore /> :
                          <MdChevronRight />
                        }
                      </span>
                      <span className="variety-sidebar-name">{variety.name}</span>
                      <RiDeleteBin6Line
                        className="variety-delete-icon"
                        onClick={(e) => deleteVariety(variety.name, e)}
                      />
                    </div>

                    {expandedVarieties[variety.name] && (
                      <div className="subvarieties-sidebar-list">
                        {variety.subVarieties.map((sub, subIdx) => (
                          <div key={subIdx} className="subvariety-sidebar-item">
                            <span className="subvariety-sidebar-name">{sub.name}</span>
                            <RiDeleteBin6Line
                              className="subvariety-delete-icon"
                              onClick={(e) => deleteSubVariety(variety.name, sub.name, e)}
                            />
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </ul>
      </aside>
    </>
  );
};

export default Sidebar;