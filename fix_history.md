# Shelfarr — UI Logic Regression TODO  
### Targeted AI-Agent Planning Prompt

You are an AI coding assistant working inside the **Shelfarr Vue 3 + Naive UI** frontend.  
Your task is to fix several small-but-important UI and UX regressions introduced during the migration from legacy Jinja/CSS → Vue SPA.

Follow the sections below. Each task must be implemented in Vue SFCs with proper reactive state, Naive UI components, and minimal global CSS use.

---

## ✅ Summary  
Restore missing behaviors from the pre-migration UI, specifically around History Mode, button visibility, loading indicators, and dynamic form logic.

All changes must follow Shelfarr architectural rules:
- **Vue 3 SPA**, no Jinja dependencies  
- **Naive UI components only**  
- Use **composables** where logic should be shared
- Use UNOcss where css is needed  
- State must be **reactive** and **persistent across navigation**

---

## 📌 Objectives  
- Restore full history logging details (success/failure + counts)  
- Fix several UI regressions introduced during refactors  
- Improve consistency with existing search + verify behaviors  
- Ensure all buttons show clear affordance and response state  

---

## 🧩 Action Items (Detailed)

### 1. **Restore History Mode File Copy Details**
Replace the placeholder text "import requested" with the original detailed status logic.

#### Requirements
- Locate the old logic in **origin/css history logic** (pre-migration code).  
  - It previously printed:
    - `"Hard linked xx file successfully"`  
    - `"Hard linked xx files unsuccessfully copied to 'import/dir/here'"`  
- Reintroduce this logic into **the Vue History component**:
  - Import summary   
  - Optional: include icons (Naive UI `<n-icon>`)

### 2. **Fix “Link to Library” Button Invisible Text**
Button shows as **green outline with no label** until clicked.

#### Requirements
- Verify the `<n-button>` props:
  - `ghost`, `text`, `secondary`, or theme overrides may be conflicting.

#### Fix Strategy
- Remove conflicting props (`text`, `ghost`)  
- Add explicit `:color`, `type="primary"` or scoped style override following glass theme

---

### 3. **Verify Button Should Show Loading Animation**
The old logic showed a loading spinner identical to the search buttons.

#### Requirements
- Add `:loading="isVerifying"` to the `<n-button>`  
- Trigger `isVerifying = true` before API call  
- Reset `isVerifying = false` in `finally` block  
- Ensure consistency with existing search button logic

#### Implementation Note
- Consider shared logic in `useSearchAndVerify()` composable:
  - Handles spinner state  
  - Standardizes transitions
  - Avoids duplicated logic

---

### 4. **Flatten Button Should Auto-Uncheck**
If user selects a torrent where **no discs are detected**, the Flatten checkbox must automatically reset to unchecked.

#### Requirements
- Watch the selected torrent:  
  ```js
  watch(() => selectedTorrent.value, (newVal) => {
    if (!newVal?.discsDetected) {
      flatten.value = false
    }
  })
