// Settings.jsx
import { useState, useEffect } from "react";
import { MdExpandMore, MdChevronRight, MdEdit, MdAdd, MdCheck, MdClose } from "react-icons/md";
import { RiDeleteBin6Line } from "react-icons/ri";
import "../styles/Settings.css";

// Utility function to get API base URL
const getApiBaseUrl = () => {
  // Check if running in Electron (exe environment)
  if (window.electron && window.electron.isElectron) {
    return 'http://localhost:5000';
  }
  // In development/web environment, use relative URLs (proxied by Vite)
  return '';
};

const Settings = () => {
  const [data, setData] = useState({ varieties: [] });
  const [toasts, setToasts] = useState([]);
  const [expandedVarieties, setExpandedVarieties] = useState({});
  const [expandedSubVarieties, setExpandedSubVarieties] = useState({});

  // Editing states
  const [editingVariety, setEditingVariety] = useState(null);
  const [editingSubVariety, setEditingSubVariety] = useState(null);
  const [editingQuality, setEditingQuality] = useState(null);
  const [editValues, setEditValues] = useState({});

  // Add new item states
  const [addingVariety, setAddingVariety] = useState(false);
  const [addingSubVariety, setAddingSubVariety] = useState(null);
  const [addingQuality, setAddingQuality] = useState(null);
  const [newItemValues, setNewItemValues] = useState({});

  useEffect(() => {
    loadData();
  }, []);

  const showToast = (message, type = "success") => {
    const id = Date.now();
    setToasts(prev => [...prev, { id, message, type }]);
    
    setTimeout(() => {
      setToasts(prev => prev.filter(toast => toast.id !== id));
    }, 3000);
  };

  const loadData = async () => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties`);
      if (response.ok) {
        const data = await response.json();
        setData(data);
        showToast("Data loaded successfully", "success");
      } else {
        setData({ varieties: [] });
        showToast("Failed to load data", "error");
      }
    } catch (error) {
      console.error("Error loading data:", error);
      setData({ varieties: [] });
      showToast("Error loading data", "error");
    }
  };

  const saveData = async (newData) => {
    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newData),
      });

      if (response.ok) {
        showToast("Data saved successfully!", "success");
        window.dispatchEvent(new CustomEvent('dataUpdated'));
      } else {
        showToast("Failed to save data", "error");
      }
    } catch (error) {
      console.error("Error saving data:", error);
      showToast("Error saving data", "error");
    }
  };

  const toggleVariety = (varietyName) => {
    setExpandedVarieties(prev => ({
      ...prev,
      [varietyName]: !prev[varietyName]
    }));
  };

  const toggleSubVariety = (varietyName, subVarietyName) => {
    const key = `${varietyName}-${subVarietyName}`;
    setExpandedSubVarieties(prev => ({
      ...prev,
      [key]: !prev[key]
    }));
  };

  // CRUD Operations
  const deleteVariety = async (varietyName) => {
    if (window.confirm(`Are you sure you want to delete "${varietyName}" and all its sub-varieties?`)) {
      try {
        const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          const newData = {
            ...data,
            varieties: data.varieties.filter(v => v.name !== varietyName)
          };
          setData(newData);
          showToast(`Variety "${varietyName}" deleted successfully`, "success");
        } else {
          showToast("Failed to delete variety", "error");
        }
      } catch (error) {
        console.error("Error deleting variety:", error);
        showToast("Error deleting variety", "error");
      }
    }
  };

  const deleteSubVariety = async (varietyName, subVarietyName) => {
    if (window.confirm(`Are you sure you want to delete sub-variety "${subVarietyName}"?`)) {
      try {
        const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(subVarietyName)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          const newData = { ...data };
          const variety = newData.varieties.find(v => v.name === varietyName);
          if (variety) {
            variety.subVarieties = variety.subVarieties.filter(s => s.name !== subVarietyName);
            setData(newData);
            showToast(`Sub-variety "${subVarietyName}" deleted successfully`, "success");
          }
        } else {
          showToast("Failed to delete sub-variety", "error");
        }
      } catch (error) {
        console.error("Error deleting sub-variety:", error);
        showToast("Error deleting sub-variety", "error");
      }
    }
  };

  const deleteQuality = async (varietyName, subVarietyName, qualityName) => {
    if (window.confirm(`Are you sure you want to delete quality "${qualityName}"?`)) {
      try {
        const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(subVarietyName)}/qualities/${encodeURIComponent(qualityName)}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          const result = await response.json();
          const newData = { ...data };
          const variety = newData.varieties.find(v => v.name === varietyName);
          if (variety) {
            const subVariety = variety.subVarieties.find(s => s.name === subVarietyName);
            if (subVariety) {
              subVariety.qualities = result.subVariety.qualities;
              setData(newData);
              showToast(`Quality "${qualityName}" deleted successfully`, "success");
            }
          }
        } else {
          showToast("Failed to delete quality", "error");
        }
      } catch (error) {
        console.error("Error deleting quality:", error);
        showToast("Error deleting quality", "error");
      }
    }
  };

  // Edit Operations
  const startEditingVariety = (varietyName) => {
    setEditingVariety(varietyName);
    setEditValues({ name: varietyName });
  };

  const startEditingSubVariety = (varietyName, subVariety) => {
    setEditingSubVariety(`${varietyName}-${subVariety.name}`);
    setEditValues({
      name: subVariety.name,
      quality: subVariety.quality,
      length: subVariety.length
    });
  };

  const startEditingQuality = (varietyName, subVarietyName, quality) => {
    setEditingQuality(`${varietyName}-${subVarietyName}-${quality.quality}`);
    setEditValues({
      quality: quality.quality,
      length: quality.length
    });
  };

  const cancelEditing = () => {
    setEditingVariety(null);
    setEditingSubVariety(null);
    setEditingQuality(null);
    setEditValues({});
  };

  const saveVarietyEdit = async () => {
    if (!editValues.name.trim()) {
      showToast("Variety name cannot be empty", "error");
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(editingVariety)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ name: editValues.name }),
      });

      if (response.ok) {
        const newData = { ...data };
        const variety = newData.varieties.find(v => v.name === editingVariety);
        if (variety) {
          variety.name = editValues.name;
          setData(newData);
          showToast("Variety updated successfully", "success");
          cancelEditing();
        }
      } else {
        const error = await response.json();
        showToast(error.error || "Failed to update variety", "error");
      }
    } catch (error) {
      console.error("Error updating variety:", error);
      showToast("Error updating variety", "error");
    }
  };

  const saveSubVarietyEdit = async (varietyName, originalSubVarietyName) => {
    if (!editValues.name.trim() || !editValues.quality.trim() || !editValues.length.trim()) {
      showToast("All fields are required", "error");
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(originalSubVarietyName)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editValues),
      });

      if (response.ok) {
        const newData = { ...data };
        const variety = newData.varieties.find(v => v.name === varietyName);
        if (variety) {
          const subVariety = variety.subVarieties.find(s => s.name === originalSubVarietyName);
          if (subVariety) {
            subVariety.name = editValues.name;
            subVariety.quality = editValues.quality;
            subVariety.length = editValues.length;
            setData(newData);
            showToast("Sub-variety updated successfully", "success");
            cancelEditing();
          }
        }
      } else {
        const error = await response.json();
        showToast(error.error || "Failed to update sub-variety", "error");
      }
    } catch (error) {
      console.error("Error updating sub-variety:", error);
      showToast("Error updating sub-variety", "error");
    }
  };

  const saveQualityEdit = async (varietyName, subVarietyName, originalQualityName) => {
    if (!editValues.quality.trim() || !editValues.length.trim()) {
      showToast("Both quality and length are required", "error");
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(subVarietyName)}/qualities/${encodeURIComponent(originalQualityName)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(editValues),
      });

      if (response.ok) {
        const result = await response.json();
        const newData = { ...data };
        const variety = newData.varieties.find(v => v.name === varietyName);
        if (variety) {
          const subVariety = variety.subVarieties.find(s => s.name === subVarietyName);
          if (subVariety) {
            subVariety.qualities = result.subVariety.qualities;
            setData(newData);
            showToast("Quality updated successfully", "success");
            cancelEditing();
          }
        }
      } else {
        const error = await response.json();
        showToast(error.error || "Failed to update quality", "error");
      }
    } catch (error) {
      console.error("Error updating quality:", error);
      showToast("Error updating quality", "error");
    }
  };

  // Add Operations
  const startAddingVariety = () => {
    setAddingVariety(true);
    setNewItemValues({ name: "" });
  };

  const startAddingSubVariety = (varietyName) => {
    setAddingSubVariety(varietyName);
    setNewItemValues({ name: "" });
  };

  const startAddingQuality = (varietyName, subVarietyName) => {
    setAddingQuality(`${varietyName}-${subVarietyName}`);
    setNewItemValues({ quality: "", length: "" });
  };

  const cancelAdding = () => {
    setAddingVariety(false);
    setAddingSubVariety(null);
    setAddingQuality(null);
    setNewItemValues({});
  };

  const saveNewVariety = async () => {
    if (!newItemValues.name.trim()) {
      showToast("Variety name cannot be empty", "error");
      return;
    }

    const varietyExists = data.varieties.some(v => v.name === newItemValues.name);
    if (varietyExists) {
      showToast("Variety already exists", "error");
      return;
    }

    const newData = {
      ...data,
      varieties: [...data.varieties, { name: newItemValues.name, subVarieties: [] }]
    };

    await saveData(newData);
    setData(newData);
    cancelAdding();
  };

  const saveNewSubVariety = async (varietyName) => {
    if (!newItemValues.name.trim()) {
      showToast("Sub-variety name cannot be empty", "error");
      return;
    }

    const newData = { ...data };
    const variety = newData.varieties.find(v => v.name === varietyName);
    if (variety) {
      const subVarietyExists = variety.subVarieties.some(s => s.name === newItemValues.name);
      if (subVarietyExists) {
        showToast("Sub-variety already exists", "error");
        return;
      }

      variety.subVarieties.push({
        name: newItemValues.name,
        qualities: []
      });

      await saveData(newData);
      setData(newData);
      cancelAdding();
    }
  };

  const saveNewQuality = async (varietyName, subVarietyName) => {
    if (!newItemValues.quality.trim() || !newItemValues.length.trim()) {
      showToast("Both quality and length are required", "error");
      return;
    }

    try {
      const response = await fetch(`${getApiBaseUrl()}/varieties/${encodeURIComponent(varietyName)}/${encodeURIComponent(subVarietyName)}/qualities`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          quality: newItemValues.quality,
          length: newItemValues.length
        }),
      });

      if (response.ok) {
        const result = await response.json();
        const newData = { ...data };
        const variety = newData.varieties.find(v => v.name === varietyName);
        if (variety) {
          const subVariety = variety.subVarieties.find(s => s.name === subVarietyName);
          if (subVariety) {
            subVariety.qualities = result.subVariety.qualities;
            setData(newData);
            showToast("Quality added successfully", "success");
            cancelAdding();
          }
        }
      } else {
        const error = await response.json();
        showToast(error.error || "Failed to add quality", "error");
      }
    } catch (error) {
      console.error("Error adding quality:", error);
      showToast("Error adding quality", "error");
    }
  };

  return (
    <div className="settings-container">
      <h2 className="settings-title">Settings</h2>

      {/* Toast Container */}
      <div className="toast-container">
        {toasts.map(toast => (
          <div key={toast.id} className={`toast toast-${toast.type}`}>
            {toast.message}
          </div>
        ))}
      </div>

      <div className="saved-data-section">
        <div className="section-header">
          <h3 className="section-title">Varieties</h3>
          <MdAdd
            className="add-icon"
            onClick={startAddingVariety}
            title="Add new variety"
          />
        </div>

        {addingVariety && (
          <div className="add-form">
            <input
              type="text"
              value={newItemValues.name || ""}
              onChange={(e) => setNewItemValues({ ...newItemValues, name: e.target.value })}
              placeholder="Variety Name"
              className="input-field-small"
              onKeyPress={(e) => e.key === 'Enter' && saveNewVariety()}
            />
            <MdCheck className="action-icon" onClick={saveNewVariety} />
            <MdClose className="action-icon" onClick={cancelAdding} />
          </div>
        )}

        {data.varieties.length === 0 && !addingVariety ? (
          <p className="empty-message">No varieties saved yet</p>
        ) : (
          <div className="varieties-list">
            {data.varieties.map((variety, idx) => (
              <div key={idx} className="variety-card">
                <div className="variety-header">
                  <div className="variety-header-left" onClick={() => toggleVariety(variety.name)}>
                    {expandedVarieties[variety.name] ?
                      <MdExpandMore className="expand-icon" /> :
                      <MdChevronRight className="expand-icon" />
                    }
                    {editingVariety === variety.name ? (
                      <input
                        type="text"
                        value={editValues.name || ""}
                        onChange={(e) => setEditValues({ ...editValues, name: e.target.value })}
                        className="edit-input"
                        onKeyPress={(e) => e.key === 'Enter' && saveVarietyEdit()}
                        autoFocus
                      />
                    ) : (
                      <h4 className="variety-name">{variety.name}</h4>
                    )}
                  </div>
                  <div className="action-buttons">
                    {editingVariety === variety.name ? (
                      <>
                        <MdCheck className="action-icon" onClick={saveVarietyEdit} />
                        <MdClose className="action-icon" onClick={cancelEditing} />
                      </>
                    ) : (
                      <>
                        <MdEdit className="action-icon" onClick={() => startEditingVariety(variety.name)} />
                        <RiDeleteBin6Line className="action-icon delete-icon" onClick={() => deleteVariety(variety.name)} />
                      </>
                    )}
                  </div>
                </div>

                {expandedVarieties[variety.name] && (
                  <div className="subvarieties-container">
                    <div className="subvariety-header-add">
                      <span>Sub-Varieties</span>
                      <MdAdd
                        className="add-icon-small"
                        onClick={() => startAddingSubVariety(variety.name)}
                        title="Add new sub-variety"
                      />
                    </div>

                    {addingSubVariety === variety.name && (
                      <div className="add-form subvariety-add-form">
                        <input
                          type="text"
                          value={newItemValues.name || ""}
                          onChange={(e) => setNewItemValues({ ...newItemValues, name: e.target.value })}
                          placeholder="Sub-Variety Name"
                          className="input-field-small"
                          onKeyPress={(e) => e.key === 'Enter' && saveNewSubVariety(variety.name)}
                        />
                        <MdCheck className="action-icon" onClick={() => saveNewSubVariety(variety.name)} />
                        <MdClose className="action-icon" onClick={cancelAdding} />
                      </div>
                    )}

                    {variety.subVarieties.map((sub, subIdx) => (
                      <div key={subIdx} className="subvariety-item">
                        <div className="subvariety-header">
                          <div className="subvariety-header-left" onClick={() => toggleSubVariety(variety.name, sub.name)}>
                            {expandedSubVarieties[`${variety.name}-${sub.name}`] ?
                              <MdExpandMore className="expand-icon-small" /> :
                              <MdChevronRight className="expand-icon-small" />
                            }
                            {editingSubVariety === `${variety.name}-${sub.name}` ? (
                              <input
                                type="text"
                                value={editValues.name || ""}
                                onChange={(e) => setEditValues({ ...editValues, name: e.target.value })}
                                className="edit-input-small"
                                placeholder="Name"
                              />
                            ) : (
                              <div className="subvariety-name">{sub.name}</div>
                            )}
                          </div>
                          <div className="action-buttons">
                            {editingSubVariety === `${variety.name}-${sub.name}` ? (
                              <>
                                <MdCheck className="action-icon-small" onClick={() => saveSubVarietyEdit(variety.name, sub.name)} />
                                <MdClose className="action-icon-small" onClick={cancelEditing} />
                              </>
                            ) : (
                              <>
                                <MdEdit className="action-icon-small" onClick={() => startEditingSubVariety(variety.name, sub)} />
                                <RiDeleteBin6Line className="action-icon-small delete-icon-small" onClick={() => deleteSubVariety(variety.name, sub.name)} />
                              </>
                            )}
                          </div>
                        </div>

                        {expandedSubVarieties[`${variety.name}-${sub.name}`] && (
                          <div className="subvariety-details">
                            <div className="qualities-header">
                              <span>Qualities</span>
                              <MdAdd
                                className="add-icon-small"
                                onClick={() => startAddingQuality(variety.name, sub.name)}
                                title="Add new quality"
                              />
                            </div>

                            {addingQuality === `${variety.name}-${sub.name}` && (
                              <div className="add-form quality-add-form">
                                <input
                                  type="text"
                                  value={newItemValues.quality || ""}
                                  onChange={(e) => setNewItemValues({ ...newItemValues, quality: e.target.value })}
                                  placeholder="Quality"
                                  className="input-field-small"
                                />
                                <input
                                  type="text"
                                  value={newItemValues.length || ""}
                                  onChange={(e) => setNewItemValues({ ...newItemValues, length: e.target.value })}
                                  placeholder="Length"
                                  className="input-field-small"
                                  onKeyPress={(e) => e.key === 'Enter' && saveNewQuality(variety.name, sub.name)}
                                />
                                <MdCheck className="action-icon" onClick={() => saveNewQuality(variety.name, sub.name)} />
                                <MdClose className="action-icon" onClick={cancelAdding} />
                              </div>
                            )}

                            {sub.qualities && sub.qualities.map((quality, qualityIdx) => (
                              <div key={qualityIdx} className="quality-item">
                                {editingQuality === `${variety.name}-${sub.name}-${quality.quality}` ? (
                                  <div className="edit-form">
                                    <input
                                      type="text"
                                      value={editValues.quality || ""}
                                      onChange={(e) => setEditValues({ ...editValues, quality: e.target.value })}
                                      placeholder="Quality"
                                      className="input-field-small"
                                    />
                                    <input
                                      type="text"
                                      value={editValues.length || ""}
                                      onChange={(e) => setEditValues({ ...editValues, length: e.target.value })}
                                      placeholder="Length"
                                      className="input-field-small"
                                      onKeyPress={(e) => e.key === 'Enter' && saveQualityEdit(variety.name, sub.name, quality.quality)}
                                    />
                                    <MdCheck className="action-icon-small" onClick={() => saveQualityEdit(variety.name, sub.name, quality.quality)} />
                                    <MdClose className="action-icon-small" onClick={cancelEditing} />
                                  </div>
                                ) : (
                                  <>
                                    <div className="quality-details">
                                      <span className="quality-label">{quality.quality}</span>
                                      <span className="length-label">{quality.length}</span>
                                    </div>
                                    <div className="action-buttons">
                                      <MdEdit className="action-icon-small" onClick={() => startEditingQuality(variety.name, sub.name, quality)} />
                                      <RiDeleteBin6Line
                                        className="action-icon-small delete-icon-small"
                                        onClick={() => deleteQuality(variety.name, sub.name, quality.quality)}
                                      />
                                    </div>
                                  </>
                                )}
                              </div>
                            ))}

                            {(!sub.qualities || sub.qualities.length === 0) && (
                              <p className="empty-message">No qualities added yet</p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Settings;