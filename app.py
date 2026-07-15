import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.lines import Line2D
from mplsoccer import Pitch

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="TutScouting - Performance Lab",
    page_icon="⚽",
    layout="wide"
)

st.title("⚽ TootScouting - Performance Lab")
st.write("---")

# 2. لوحة التحكم الجانبية (Sidebar)
st.sidebar.header("📁 تحميل البيانات")
uploaded_file = st.sidebar.file_uploader("ارفع ملف المباراة (Excel أو CSV)", type=["csv", "xlsx"])

# إعداد شكل الملعب الافتراضي
pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a1a', line_color='#7c7c7c')

# 3. معالجة البيانات التكتيكية بعد الرفع
if uploaded_file is not None:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        try:
            df = pd.read_excel(uploaded_file, sheet_name='كل الأحداث', engine='openpyxl')
        except:
            try:
                df = pd.read_excel(uploaded_file, sheet_name='All Actions', engine='openpyxl')
            except:
                df = pd.read_excel(uploaded_file, engine='openpyxl')
            
    df.columns = df.columns.astype(str).str.strip()
    
    # خريطة ذكية لتوحيد مسميات الأعمدة
    rename_dict = {}
    for col in df.columns:
        c_low = col.lower()
        if c_low in ['x start', 'x_start', 'x1', 'start x', 'pos x']: rename_dict[col] = 'x1'
        elif c_low in ['y start', 'y_start', 'y1', 'start y', 'pos y']: rename_dict[col] = 'y1'
        elif c_low in ['x end', 'x_end', 'x2', 'end x', 'pos x2']: rename_dict[col] = 'x2'
        elif c_low in ['y end', 'y_end', 'y2', 'end y', 'pos y2']: rename_dict[col] = 'y2'
        elif c_low in ['player', 'اللاعب', 'لاعب']: rename_dict[col] = 'Player'
        elif c_low in ['action', 'الأكشن', 'حدث', 'event']: rename_dict[col] = 'Action'

    df = df.rename(columns=rename_dict)
    
    if isinstance(df.get('Action'), pd.DataFrame):
        df['Action_Clean'] = df['Action'].iloc[:, 0].fillna('Other').astype(str).str.strip()
    elif 'Action' in df.columns:
        df['Action_Clean'] = df['Action'].fillna('Other').astype(str).str.strip()
    else:
        df['Action_Clean'] = 'Other'
    
    if 'x1' in df.columns and 'y1' in df.columns:
        
        for col in ['x1', 'y1', 'x2', 'y2']:
            if col in df.columns:
                if isinstance(df[col], pd.DataFrame):
                    df[col] = df[col].iloc[:, 0]
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # تحجيم الإحداثيات (Scaling)
        if df['x1'].max() <= 1.0 and df['y1'].max() <= 1.0:
            df['x_scaled'] = df['x1'] * 120
            df['y_scaled'] = df['y1'] * 80
            df['x2_scaled'] = df['x2'] * 120 if 'x2' in df.columns else np.nan
            df['y2_scaled'] = df['y2'] * 80 if 'y2' in df.columns else np.nan
        else:
            df['x_scaled'], df['y_scaled'] = df['x1'], df['y1']
            df['x2_scaled'] = df['x2'] if 'x2' in df.columns else np.nan
            df['y2_scaled'] = df['y2'] if 'y2' in df.columns else np.nan

        # تصنيف الأكشن تكتيكياً
        def classify_action(val):
            val = val.lower()
            if 'pass' in val or 'تمرير' in val: return "Pass"
            if 'shot' in val or 'sh/a' in val or 'تسديد' in val: return "Shot"
            if 'tackle' in val or 'تدخل' in val or 'pressing' in val or 'ضغط' in val or 'counter' in val: return "Defensive Action"
            if 'clearance' in val or 'تشتيت' in val or 'تخليص' in val: return "Clearance"
            if 'interception' in val or 'extraction' in val or 'قطع' in val: return "Interception"
            if 'aerial' in val or 'هوائي' in val: return "Aerial Duel"
            if 'ground' in val or 'أرضي' in val: return "Ground Duel"
            if 'dribble' in val or 'مراوغة' in val or 'ترقيص' in val: return "Dribble"
            if 'miscontrol' in val or 'فقد' in val: return "Miscontrol"
            if 'foul' in val or 'خطأ' in val: return "Foul"
            if 'kick-off' in val or 'بداية' in val: return "Kick-off"
            return "Other Actions"

        df['Event_Type'] = df['Action_Clean'].apply(classify_action)

        # 4. فلاتر العرض التفاعلية (Sidebar Filters)
        st.sidebar.write("---")
        st.sidebar.header("🔍 فلاتر الملعب")
        
        # فلتر نوع العرض تكتيكياً (مخطط أحداث أم خريطة حرارية)
        map_type = st.sidebar.radio("اختر نوع العرض على الملعب:", ["مخطط الأحداث (Event Map)", "الخريطة الحرارية (Heatmap)"])
        
        # فلتر اللاعبين
        if 'Player' in df.columns:
            if isinstance(df['Player'], pd.DataFrame):
                df['Player'] = df['Player'].iloc[:, 0]
            players = ["جميع اللاعبين (الفريق)"] + sorted(df['Player'].dropna().astype(str).unique().tolist())
        else:
            players = ["جميع اللاعبين (الفريق)"]
            
        selected_player = st.sidebar.selectbox("اختر اللاعب أو الفريق:", players)
        
        # فلتر الأحداث
        available_events = sorted(df['Event_Type'].unique().tolist())
        selected_events = st.sidebar.multiselect("اختر الأحداث المشمولة في التحليل:", options=available_events, default=available_events)
        
        # تطبيق الفلترة على البيانات
        filtered_df = df
        if selected_player != "جميع اللاعبين (الفريق)" and 'Player' in df.columns:
            filtered_df = df[df['Player'].astype(str) == selected_player]
            
        filtered_df = filtered_df[filtered_df['Event_Type'].isin(selected_events)].dropna(subset=['x_scaled', 'y_scaled'])
        
        st.write("---")
        st.subheader(f"📊 خطوة 2: {map_type}")

        # تقسيم الشاشة
        col_stats, col_pitch = st.columns([1, 2.5])

        with col_stats:
            st.markdown("### 📈 ملخص سريع")
            st.metric(label="إجمالي الأحداث المعروضة", value=len(filtered_df))
            st.write("---")
            # عرض توزيع الأحداث المفلترة كنسبة مئوية
            if not filtered_df.empty:
                st.markdown("**توزيع الأحداث الحالي:**")
                event_counts = filtered_df['Event_Type'].value_counts()
                st.write(event_counts)

        with col_pitch:
            fig, ax = plt.subplots(figsize=(12, 9))
            pitch.draw(ax=ax)
            fig.patch.set_facecolor('#1a1a1a')
            
            display_name = "All Players" if selected_player == "جميع اللاعبين (الفريق)" else selected_player
            ax.text(60, 40, display_name, color='#D4AF37', fontsize=50, fontweight='bold', 
                    ha='center', va='center', alpha=0.08, zorder=1)

            # 🔘 الحالة الأولى: الخريطة الحرارية (Heatmap)
            if map_type == "الخريطة الحرارية (Heatmap)":
                if len(filtered_df) > 2:  # الـ KDE يحتاج على الأقل نقطتين أو 3 لرسم المنحنى
                    # رسم الخريطة الحرارية بنعومة وبألوان نارية تليق بالخلفية الغامقة
                    sns.kdeplot(
                        x=filtered_df['x_scaled'], 
                        y=filtered_df['y_scaled'], 
                        ax=ax, 
                        fill=True, 
                        cmap="hot", 
                        alpha=0.6, 
                        thresh=0.05, 
                        levels=100,
                        zorder=2
                    )
                else:
                    st.warning("⚠️ البيانات المتاحة قليلة جداً لرسم خريطة حرارية دقيقة لهذا الفلتر. يرجى اختيار أحداث أكثر.")
            
            # 🔘 الحالة الثانية: مخطط الأحداث العادي (Event Map)
            else:
                event_configs = {
                    "Pass": {"color": "#00ffcc", "marker": None, "is_arrow": True},
                    "Shot": {"color": "#00ff00", "marker": "*"},
                    "Defensive Action": {"color": "#ff00ff", "marker": "X"},
                    "Interception": {"color": "#FFFF00", "marker": "o"},
                    "Clearance": {"color": "#ffffff", "marker": "s"},
                    "Aerial Duel": {"color": "#3399ff", "marker": "^"},
                    "Ground Duel": {"color": "#8B4513", "marker": "v"},
                    "Dribble": {"color": "#ff9900", "marker": "P"},
                    "Miscontrol": {"color": "#ff3333", "marker": "h"},
                    "Foul": {"color": "#ccff00", "marker": "d"},
                    "Kick-off": {"color": "#9933ff", "marker": "p"},
                    "Other Actions": {"color": "#aaaaaa", "marker": "o"}
                }

                legend_elements = []
                for event in selected_events:
                    if event not in event_configs: continue
                    cfg = event_configs[event]
                    subset = filtered_df[filtered_df['Event_Type'] == event]
                    
                    if subset.empty: continue
                    
                    if cfg.get("is_arrow"):
                        arrow_df = subset.dropna(subset=['x2_scaled', 'y2_scaled'])
                        if not arrow_df.empty:
                            pitch.arrows(arrow_df['x_scaled'], arrow_df['y_scaled'], 
                                         arrow_df['x2_scaled'], arrow_df['y2_scaled'], 
                                         color=cfg['color'], width=2, ax=ax, zorder=3)
                            legend_elements.append(Line2D([0], [0], color=cfg['color'], lw=2, label=event))
                    else:
                        pitch.scatter(subset['x_scaled'], subset['y_scaled'], 
                                      color=cfg['color'], marker=cfg['marker'], s=150, ax=ax, zorder=3)
                        legend_elements.append(Line2D([0], [0], marker=cfg['marker'], color='none', 
                                                      markerfacecolor=cfg['color'], markeredgecolor=cfg['color'], 
                                                      label=event, markersize=10))

                if legend_elements:
                    ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.05), 
                              ncol=4, facecolor='#222222', labelcolor='white', fontsize=11)
            
            st.pyplot(fig)
            plt.close(fig)
        
        # عرض الجدول
        st.write("---")
        st.subheader("📊 جدول البيانات المفلترة")
        team_col = 'Team Tag' if 'Team Tag' in df.columns else ('Team' if 'Team' in df.columns else 'Action_Clean')
        start_col = 'Start' if 'Start' in df.columns else ('Start (mm:ss)' if 'Start (mm:ss)' in df.columns else 'Action_Clean')
        
        show_cols = ['Action_Clean', 'Player']
        if team_col in df.columns: show_cols.append(team_col)
        if start_col in df.columns: show_cols.append(start_col)
        
        st.dataframe(filtered_df[show_cols].reset_index(drop=True), use_container_width=True)
        
    else:
        st.error("⚠️ لم نتمكن من تحديد أعمدة الإحداثيات في الملف المرفوع.")
else:
    fig, ax = plt.subplots(figsize=(12, 8))
    pitch.draw(ax=ax)
    fig.patch.set_facecolor('#1a1a1a')
    st.pyplot(fig)
    plt.close(fig)
    st.info("💡 لوحة التحليل جاهزة. يرجى رفع ملف المباراة للبدء.")
