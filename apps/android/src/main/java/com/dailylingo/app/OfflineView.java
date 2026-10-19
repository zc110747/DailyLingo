package com.dailylingo.app;

import android.content.Context;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.View;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

/**
 * 错误菜单：没有网络、连不上站点、或者导航失败时显示。
 *
 * <p>纯原生控件（不用 Material 库），外观对齐桌面端：浅灰底 + 白色圆角卡片 +
 * 主按钮实心蓝、次按钮白底描边。</p>
 */
final class OfflineView extends ScrollView {

    interface Listener {
        void onRetry();

        void onOpenInBrowser();
    }

    private final TextView mHeadline;
    private final TextView mDetail;
    private final TextView mProgress;

    OfflineView(Context context) {
        super(context);

        setBackgroundColor(color(R.color.page_background));
        setFillViewport(true);

        LinearLayout centering = new LinearLayout(context);
        centering.setOrientation(LinearLayout.VERTICAL);
        centering.setGravity(Gravity.CENTER);
        centering.setPadding(dp(24), dp(32), dp(24), dp(32));
        addView(centering, new LayoutParams(LayoutParams.MATCH_PARENT, LayoutParams.WRAP_CONTENT));

        LinearLayout card = new LinearLayout(context);
        card.setOrientation(LinearLayout.VERTICAL);
        card.setPadding(dp(24), dp(24), dp(24), dp(24));

        GradientDrawable cardBackground = new GradientDrawable();
        cardBackground.setColor(color(R.color.card_background));
        cardBackground.setCornerRadius(dp(16));
        cardBackground.setStroke(dp(1), color(R.color.card_border));
        card.setBackground(cardBackground);

        centering.addView(card, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT));

        mHeadline = new TextView(context);
        mHeadline.setTextSize(TypedValue.COMPLEX_UNIT_SP, 19f);
        mHeadline.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        mHeadline.setTextColor(color(R.color.title_text));
        card.addView(mHeadline);

        mDetail = new TextView(context);
        mDetail.setTextSize(TypedValue.COMPLEX_UNIT_SP, 14f);
        mDetail.setTextColor(color(R.color.muted_text));
        mDetail.setLineSpacing(dp(3), 1f);
        LinearLayout.LayoutParams detailParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        detailParams.topMargin = dp(10);
        card.addView(mDetail, detailParams);

        mProgress = new TextView(context);
        mProgress.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12.5f);
        mProgress.setTextColor(color(R.color.muted_text));
        mProgress.setLineSpacing(dp(2), 1f);
        LinearLayout.LayoutParams progressParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        progressParams.topMargin = dp(10);
        card.addView(mProgress, progressParams);

        TextView retry = createButton(context, context.getString(R.string.offline_retry), true);
        LinearLayout.LayoutParams retryParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(46));
        retryParams.topMargin = dp(22);
        card.addView(retry, retryParams);

        TextView browser = createButton(context, context.getString(R.string.offline_browser), false);
        LinearLayout.LayoutParams browserParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, dp(46));
        browserParams.topMargin = dp(10);
        card.addView(browser, browserParams);
    }

    void bindActions(final Listener listener) {
        // 按钮在构造时按顺序添加：card 里倒数第二个是重试，最后一个是浏览器。
        LinearLayout card = (LinearLayout) ((LinearLayout) getChildAt(0)).getChildAt(0);
        int count = card.getChildCount();

        card.getChildAt(count - 2).setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View view) {
                listener.onRetry();
            }
        });

        card.getChildAt(count - 1).setOnClickListener(new OnClickListener() {
            @Override
            public void onClick(View view) {
                listener.onOpenInBrowser();
            }
        });
    }

    void setContent(String headline, String detail, String progress) {
        mHeadline.setText(headline);
        mDetail.setText(detail);
        mProgress.setText(progress);
    }

    private TextView createButton(Context context, String text, boolean primary) {
        TextView button = new TextView(context);
        button.setText(text);
        button.setTextSize(TypedValue.COMPLEX_UNIT_SP, 15f);
        button.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        button.setGravity(Gravity.CENTER);
        button.setClickable(true);
        button.setFocusable(true);

        GradientDrawable background = new GradientDrawable();
        background.setCornerRadius(dp(10));
        if (primary) {
            background.setColor(color(R.color.accent));
            // 主按钮用纯白字（卡片色 #FFFFFF 与纯白等价，这里直接写死避免歧义）。
            button.setTextColor(0xFFFFFFFF);
        } else {
            background.setColor(color(R.color.card_background));
            background.setStroke(dp(1), color(R.color.card_border));
            button.setTextColor(color(R.color.title_text));
        }
        button.setBackground(background);

        return button;
    }

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private int color(int id) {
        return getResources().getColor(id, getContext().getTheme());
    }
}
