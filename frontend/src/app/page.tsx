import { HomeHero } from "@/components/home/HomeHero";
import { ExploreList, ScreenerStats, SplitStory } from "@/components/home/HomeSections";

export default function Home() {
  return (
    <>
      <div className="page-wrap">
        <HomeHero />
      </div>
      <SplitStory />
      <div className="page-wrap">
        <ScreenerStats />
        <ExploreList />
      </div>
    </>
  );
}
