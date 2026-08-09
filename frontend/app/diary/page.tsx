import { DiaryList } from "@/components/diary-list";

export default function DiaryPage() {
  return (
    <main>
      <h1>Diary</h1>
      <p style={{ color: "var(--muted)", marginTop: "0.5rem" }}>
        Your theatre history, newest attendance first.
      </p>
      <DiaryList />
    </main>
  );
}
