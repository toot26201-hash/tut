import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
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

# إعداد شكل الملعب الافتراضي في الصفحة الرئيسية
pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a1a', line_color='#7c7c7c')

# 3. معالجة البيانات التكتيكية بعد الرفع
if uploaded_file is not None:
    # قراءة الملف بمرونة بناءً على نوعه
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        try:
            # محاولة قراءة الشيت المخصص لو موجود
            df = pd.read_excel(uploaded_file, sheet_name='كل الأحداث', engine='openpyxl')
        except:
            df = pd.read_excel(uploaded_file, engine='openpyxl')
            
    # تنظيف أسماء الأعمدة من أي مسافات وتحويلها لنص
    df.columns = df.columns.astype(str).str.strip()
    
    # خريطة ذكية لتوحيد مسميات الأعمدة (سواء كابيتال أو سمول أو عربي)
    rename_dict = {}
    for col in df.columns:
        c_low = col.lower()
        if c_low in ['x start', 'x_start', 'x1', 'start x', 'pos x']: rename_dict[col] = 'x1'
        elif c_low in ['y start', 'y_start', 'y1', 'start y', 'pos y']: rename_dict[col] = 'y1'
        elif c_low in ['x end', 'x_end', 'x2', 'end x', 'pos x2']: rename_dict[col] = 'x2'
        elif c_low in ['y end', 'y_end', 'y2', 'end y', 'pos y2']: rename_dict[col] = 'y2'
        elif c_low in ['player', 'اللاعب', 'لاعب']: rename_dict[col] = 'Player'
        elif c_low in ['action', 'الأكشن', 'حدث', 'event']: rename_dict[col] = 'Action'

    # إعادة تسمية الأعمدة بناءً على الفحص الذكي
    df = df.rename(columns=rename_dict)
    
    # حل مشكلة تكرار اسم عمود Action لو وجد
    if isinstance(df.get('Action'), pd.DataFrame):
        # لو رجع جدول بسبب التكرار ناخد أول عمود فيه
        df['Action_Clean'] = df['Action'].iloc[:, 0].fillna('Other').astype(str).str.strip()
    elif 'Action' in df.columns:
        df['Action_Clean'] = df['Action'].fillna('Other').astype(str).str.strip()
    else:
        df['Action_Clean'] = 'Other'
    
    # التأكد من وجود الإحداثيات الأساسية لبدء التحليل
    if 'x1' in df.columns and 'y1' in df.columns:
        
        # تحويل الإحداثيات لأرقام ومعالجة القيم المفقودة
        for col in ['x1', 'y1', 'x2', 'y2']:
            if col in df.columns:
                if isinstance(df[col], pd.DataFrame): # حماية ضد الأعمدة المكررة
                    df[col] = df[col].iloc[:, 0]
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # تحجيم الإحداثيات (Scaling) بناءً على نوع الإدخال (نسبة مئوية أم أبعاد فعلية)
        if df['x1'].max() <= 1.0 and df['y1'].max() <= 1.0:
            df['x_scaled'] = df['x1'] * 120
            df['y_scaled'] = df['y1'] * 80
            df['x2_scaled'] = df['x2'] * 120 if 'x2' in df.columns else np.nan
            df['y2_scaled'] = df['y2'] * 80 if 'y2' in df.columns else np.nan
        else:
            df['x_scaled'], df['y_scaled'] = df['x1'], df['y1']
            df['x2_scaled'] = df['x2'] if 'x2' in df.columns else np.nan
            df['y2_scaled'] = df['y2'] if 'y2' in df.columns else np.nan

        # تصنيف الأكشن تكتيكياً بناءً على محتوى الملف الجديد
        def classify_action(val):
            val = val.lower()
            if 'pass' in val or 'تمرير' in val: return "Pass"
            if 'shot' in val or 'sh/a' in val or 'تسديد' in val: return "Shot"
            if 'tackle' in val or 'تدخل' in val or 'pressing' in val or 'ضغط' in val or 'counter' in val: return "Defensive Action"
            if 'clearance' in val or 'تشتيت' in val or 'تخليص' in val: return "Clearance"
            if 'interception' in val or 'extraction' in val or 'قطع' in val: return "Interception"
            if 'aerial' in val or 'هوائي' in val: return "Aerial Duel"
            if 'ground' in val or 'أرضي' in val: return "Ground Duel"
            return "Other"

        df['Event_Type'] = df['Action_Clean'].apply(classify_action)

        # 4. فلاتر العرض التفاعلية (Sidebar Filters)
        st.sidebar.write("---")
        st.sidebar.header("🔍 فلاتر الملعب")
        
        # فلتر اللاعبين
        if 'Player' in df.columns:
            if isinstance(df['Player'], pd.DataFrame):
                df['Player'] = df['Player'].iloc[:, 0]
            players = ["جميع اللاعبين"] + sorted(df['Player'].dropna().astype(str).unique().tolist())
        else:
            players = ["جميع اللاعبين"]
            
        selected_player = st.sidebar.selectbox("اختر اللاعب:", players)
        
        # فلتر الأحداث
        available_events = sorted(df['Event_Type'].unique().tolist())
        selected_events = st.sidebar.multiselect("اختر الأحداث للعرض:", options=available_events, default=available_events)
        
        # تطبيق الفلترة على البيانات
        filtered_df = df
        if selected_player != "جميع اللاعبين" and 'Player' in df.columns:
            filtered_df = df[df['Player'].astype(str) == selected_player]
            
        filtered_df = filtered_df[filtered_df['Event_Type'].isin(selected_events)]
        
        # 5. رسم الملعب والبيانات المفلترة
        fig, ax = plt.subplots(figsize=(12, 9))
        pitch.draw(ax=ax)
        fig.patch.set_facecolor('#1a1a1a')
        
        # إضافة اسم اللاعب كعلامة مائية خفيفة في وسط الملعب
        display_name = "All Players" if selected_player == "جميع اللاعبين" else selected_player
        ax.text(60, 40, display_name, color='#D4AF37', fontsize=50, fontweight='bold', 
                ha='center', va='center', alpha=0.08, zorder=1)

        # إعدادات الألوان والأشكال لكل حدث تكتيكي
        event_configs = {
            "Pass": {"color": "#00ffcc", "marker": None, "is_arrow": True},
            "Shot": {"color": "#00ff00", "marker": "*"},
            "Defensive Action": {"color": "#ff00ff", "marker": "X"},
            "Interception": {"color": "#FFFF00", "marker": "o"},
            "Clearance": {"color": "#ffffff", "marker": "s"},
            "Aerial Duel": {"color": "#3399ff", "marker": "^"},
            "Ground Duel": {"color": "#8B4513", "marker": "v"},
            "Other": {"color": "#aaaaaa", "marker": "d"}
        }

        legend_elements = []
        
        for event in selected_events:
            if event not in event_configs: continue
            cfg = event_configs[event]
            subset = filtered_df[filtered_df['Event_Type'] == event].dropna(subset=['x_scaled', 'y_scaled'])
            
            if subset.empty: continue
            
            # رسم التمريرات كأسهم حركية
            if cfg.get("is_arrow"):
                arrow_df = subset.dropna(subset=['x2_scaled', 'y2_scaled'])
                if not arrow_df.empty:
                    pitch.arrows(arrow_df['x_scaled'], arrow_df['y_scaled'], 
                                 arrow_df['x2_scaled'], arrow_df['y2_scaled'], 
                                 color=cfg['color'], width=2, ax=ax, zorder=2)
                    legend_elements.append(Line2D([0], [0], color=cfg['color'], lw=2, label=event))
            # رسم باقي الأحداث كنقاط مميزة
            else:
                pitch.scatter(subset['x_scaled'], subset['y_scaled'], 
                              color=cfg['color'], marker=cfg['marker'], s=150, ax=ax, zorder=2)
                legend_elements.append(Line2D([0], [0], marker=cfg['marker'], color='none', 
                                              markerfacecolor=cfg['color'], markeredgecolor=cfg['color'], 
                                              label=event, markersize=10))

        # عرض دليل الألوان أسفل الملعب
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper center', bbox_to_anchor=(0.5, -0.05), 
                      ncol=4, facecolor='#222222', labelcolor='white', fontsize=11)
        
        # عرض الملعب في الصفحة الرئيسية
        st.pyplot(fig)
        plt.close(fig)
        
        # عرض جدول البيانات المفلترة أسفل الملعب للمراجعة السريعة
        st.write("---")
        st.subheader("📊 جدول البيانات المفلترة")
        st.dataframe(filtered_df[['Action_Clean', 'Player', 'Team Tag', 'Start']].reset_index(drop=True), use_container_width=True)
        
    else:
        st.error("⚠️ لم نتمكن من تحديد أعمدة الإحداثيات في الملف المرفوع. يرجى مراجعة عناوين الجدول.")
else:
    # شاشة ترحيبية نظيفة تظهر عند فتح التطبيق لأول مرة
    fig, ax = plt.subplots(figsize=(12, 8))
    pitch.draw(ax=ax)
    fig.patch.set_facecolor('#1a1a1a')
    st.pyplot(fig)
    plt.close(fig)
    st.info("💡 لوحة التحليل جاهزة. يرجى رفع ملف المباراة الجديد من القائمة الجانبية للبدء.")
